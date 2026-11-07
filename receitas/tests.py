"""
Testes do domínio de receitas: models (spec 001), views públicas de
listagem/detalhe (spec 002), comentários (spec 005), limite de taxa (spec
006) e honeypot/time-trap (spec 007) na criação de comentário.

Estratégia de isolamento: tudo aqui é ORM/HTTP de teste do Django rodando
contra o banco de teste do pytest-django (``@pytest.mark.django_db``) — sem
mock. Não há I/O externo (rede, storage remoto) neste domínio ainda; o
upload de imagem usa ``SimpleUploadedFile`` em memória. O cache é limpo antes
de cada teste (fixture autouse) para os contadores de limitação de taxa não
vazarem de um teste para o outro.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .forms import _ASSINATURA_SALT
from .models import Categoria, Comentario, Receita, Tag

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def _limpar_cache_de_limitacao() -> None:
    """Zera os contadores de limitação de taxa antes de cada teste (spec 006)."""
    cache.clear()


# -----------------------------------------------------------------------------
# Builders
# -----------------------------------------------------------------------------
def _categoria(**kwargs: Any) -> Categoria:
    """
    Cria uma Categoria com defaults sensatos, sobrescrevíveis por teste.

    Args:
        **kwargs (Any): campos que sobrescrevem o default (``nome``, etc.).

    Returns:
        Categoria: instância já persistida.
    """
    dados = {"nome": "Sobremesas"}
    dados.update(kwargs)
    return Categoria.objects.create(**dados)


def _tag(**kwargs: Any) -> Tag:
    """
    Cria uma Tag com defaults sensatos, sobrescrevíveis por teste.

    Args:
        **kwargs (Any): campos que sobrescrevem o default (``nome``, etc.).

    Returns:
        Tag: instância já persistida.
    """
    dados = {"nome": "Vegana"}
    dados.update(kwargs)
    return Tag.objects.create(**dados)


def _receita(**kwargs: Any) -> Receita:
    """
    Cria uma Receita mínima válida, sobrescrevível por teste.

    Args:
        **kwargs (Any): campos que sobrescrevem o default (``titulo``,
            ``categoria``, ``autor``, etc.).

    Returns:
        Receita: instância já persistida.
    """
    dados: dict[str, Any] = {
        "titulo": "Bolo de cenoura",
        "resumo": "Um clássico simples de fazer.",
        "ingredientes": "2 cenouras\n3 ovos\n2 xícaras de farinha",
        "modo_de_preparo": "Bata tudo no liquidificador e asse por 40 minutos.",
        "tempo_preparo_minutos": 50,
        "porcoes": 8,
        "categoria": kwargs.pop("categoria", None) or _categoria(),
    }
    dados.update(kwargs)
    return Receita.objects.create(**dados)


def _comentario(**kwargs: Any) -> Comentario:
    """
    Cria um Comentario mínimo válido, sobrescrevível por teste.

    Args:
        **kwargs (Any): campos que sobrescrevem o default (``receita``,
            ``autor``, ``texto``, ``aprovado``, etc.).

    Returns:
        Comentario: instância já persistida.
    """
    # "autor" in kwargs (mesmo que None) é diferente de "não informado" —
    # precisa distinguir pra permitir testar comentário sem autor.
    if "autor" in kwargs:
        autor = kwargs.pop("autor")
    else:
        # username único por chamada — testes que criam vários comentários
        # sem passar autor não podem colidir no username.
        autor = User.objects.create_user(
            username=f"comentarista-{uuid4().hex[:8]}", password="senha-forte-123"
        )
    dados: dict[str, Any] = {
        "receita": kwargs.pop("receita", None) or _receita(publicado=True),
        "autor": autor,
        "texto": "Ficou ótimo, testei e aprovei!",
    }
    dados.update(kwargs)
    return Comentario.objects.create(**dados)


def _carimbo_valido(segundos_atras: float = 5) -> str:
    """
    Gera um carimbo assinado como se tivesse sido renderizado há N segundos.

    Args:
        segundos_atras (float): há quantos segundos simular que o
            formulário foi renderizado. Default (5s) passa no time-trap
            (mínimo de 2s); passar 0 simula um envio no mesmo instante.

    Returns:
        str: valor pronto para o campo ``carimbo_tempo`` do POST (spec 007).
    """
    return signing.dumps(time.time() - segundos_atras, salt=_ASSINATURA_SALT)


# -----------------------------------------------------------------------------
# Slug único (RF-01, RF-02)
# -----------------------------------------------------------------------------
def test_categoria_gera_slug_a_partir_do_nome() -> None:
    categoria = _categoria(nome="Pratos Rápidos")
    assert categoria.slug == "pratos-rapidos"


def test_categoria_com_nome_repetido_gera_slug_com_sufixo() -> None:
    """Duas categorias com o mesmo nome não colidem no slug (RF-01)."""
    primeira = _categoria(nome="Sobremesas")
    segunda = _categoria(nome="Sobremesas")

    assert primeira.slug == "sobremesas"
    assert segunda.slug == "sobremesas-2"


def test_tag_com_nome_repetido_gera_slug_com_sufixo() -> None:
    primeira = _tag(nome="sem glúten")
    segunda = _tag(nome="sem glúten")

    assert primeira.slug == "sem-gluten"
    assert segunda.slug == "sem-gluten-2"


# -----------------------------------------------------------------------------
# Relacionamentos e defaults (RF-03, RNF-01)
# -----------------------------------------------------------------------------
def test_receita_nasce_como_rascunho_com_timestamps() -> None:
    receita = _receita()

    assert receita.publicado is False
    assert receita.slug == "bolo-de-cenoura"
    assert receita.criado_em is not None
    assert receita.atualizado_em is not None


def test_excluir_categoria_em_uso_e_bloqueado() -> None:
    """``on_delete=PROTECT`` impede apagar uma categoria com receita associada."""
    categoria = _categoria()
    _receita(categoria=categoria)

    with pytest.raises(ProtectedError):
        categoria.delete()


def test_excluir_tag_nao_afeta_a_receita() -> None:
    tag = _tag()
    receita = _receita()
    receita.tags.add(tag)

    tag.delete()

    receita.refresh_from_db()
    assert receita.tags.count() == 0


def test_excluir_autor_preserva_a_receita_sem_autor() -> None:
    """``on_delete=SET_NULL`` preserva o conteúdo mesmo sem o usuário (ADR-2)."""
    autor = User.objects.create_user(username="cozinheira", password="senha-forte-123")
    receita = _receita(autor=autor)

    autor.delete()

    receita.refresh_from_db()
    assert receita.autor is None


# -----------------------------------------------------------------------------
# Validação de imagem de capa (RF-04)
# -----------------------------------------------------------------------------
def test_imagem_muito_grande_e_rejeitada() -> None:
    arquivo_grande = SimpleUploadedFile(
        "capa.jpg",
        b"0" * (5 * 1024 * 1024 + 1),
        content_type="image/jpeg",
    )
    receita = _receita(imagem_capa=arquivo_grande)

    with pytest.raises(ValidationError):
        receita.full_clean()


def test_extensao_de_imagem_invalida_e_rejeitada() -> None:
    arquivo_invalido = SimpleUploadedFile(
        "capa.txt",
        b"nao e uma imagem",
        content_type="text/plain",
    )
    receita = _receita(imagem_capa=arquivo_invalido)

    with pytest.raises(ValidationError):
        receita.full_clean()


def test_receita_sem_imagem_e_valida() -> None:
    receita = _receita()

    receita.full_clean()  # não deve levantar


# -----------------------------------------------------------------------------
# Admin (RF-05)
# -----------------------------------------------------------------------------
def test_listagens_do_admin_respondem_200(client: Client) -> None:
    staff = User.objects.create_user(
        username="admin-teste",
        password="senha-forte-123",
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(staff)

    for url in [
        "/admin/receitas/categoria/",
        "/admin/receitas/tag/",
        "/admin/receitas/receita/",
    ]:
        resposta = client.get(url)
        assert resposta.status_code == 200


# -----------------------------------------------------------------------------
# Listagem pública (RF-01, RF-02, RNF-01)
# -----------------------------------------------------------------------------
def test_listagem_mostra_somente_publicadas(client: Client) -> None:
    publicada = _receita(titulo="Receita publicada", publicado=True)
    _receita(titulo="Receita rascunho", publicado=False)

    resposta = client.get(reverse("receitas:lista"))

    conteudo = resposta.content.decode()
    assert publicada.titulo in conteudo
    assert "Receita rascunho" not in conteudo


def test_listagem_ordena_mais_recentes_primeiro(client: Client) -> None:
    mais_antiga = _receita(titulo="Receita antiga", publicado=True)
    mais_nova = _receita(titulo="Receita nova", publicado=True)
    # O auto_now_add empata quando as duas receitas nascem no mesmo tick do relógio
    # (Windows com Python < 3.13, ~15 ms); datas explícitas fixam a ordem.
    Receita.objects.filter(pk=mais_antiga.pk).update(
        criado_em=timezone.now() - timedelta(days=1)
    )

    resposta = client.get(reverse("receitas:lista"))

    titulos = [r.titulo for r in resposta.context["receitas"]]
    assert titulos.index(mais_nova.titulo) < titulos.index(mais_antiga.titulo)


def test_listagem_pagina_com_mais_de_9_receitas(client: Client) -> None:
    categoria = _categoria()
    for i in range(10):
        _receita(titulo=f"Receita {i}", categoria=categoria, publicado=True)

    primeira_pagina = client.get(reverse("receitas:lista"))
    segunda_pagina = client.get(reverse("receitas:lista"), {"page": 2})

    assert len(primeira_pagina.context["receitas"]) == 9
    assert len(segunda_pagina.context["receitas"]) == 1


def test_listagem_pagina_inexistente_retorna_404(client: Client) -> None:
    _receita(publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"page": 999})

    assert resposta.status_code == 404


def test_listagem_nao_tem_n_mais_1_com_tags(
    client: Client, django_assert_num_queries: Any
) -> None:
    """``select_related``/``prefetch_related`` mantêm a query constante (RNF-01)."""
    categoria = _categoria()
    for i in range(3):
        receita = _receita(titulo=f"Receita {i}", categoria=categoria, publicado=True)
        receita.tags.add(_tag(nome=f"tag-{i}-a"), _tag(nome=f"tag-{i}-b"))

    # 1 count (paginação) + 1 select principal (join de categoria/autor) + 1
    # prefetch de tags — não cresce com o número de receitas nem de tags.
    with django_assert_num_queries(3):
        client.get(reverse("receitas:lista"))


# -----------------------------------------------------------------------------
# Busca e filtros (RF-01 a RF-06, RNF-02)
# -----------------------------------------------------------------------------
def test_busca_por_titulo_encontra_receita(client: Client) -> None:
    receita = _receita(titulo="Bolo de cenoura", publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"q": "cenoura"})

    assert receita.titulo in [r.titulo for r in resposta.context["receitas"]]


def test_busca_por_ingrediente_encontra_receita(client: Client) -> None:
    """O termo "cenoura" só aparece em ``ingredientes``, não no título (RF-01)."""
    receita = _receita(
        titulo="Bolo simples", ingredientes="2 cenouras\n1 ovo", publicado=True
    )

    resposta = client.get(reverse("receitas:lista"), {"q": "cenoura"})

    assert receita.titulo in [r.titulo for r in resposta.context["receitas"]]


def test_busca_sem_correspondencia_nao_encontra_nada(client: Client) -> None:
    _receita(titulo="Bolo de cenoura", publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"q": "abobora"})

    assert list(resposta.context["receitas"]) == []


def test_filtro_por_categoria_existente(client: Client) -> None:
    sobremesas = _categoria(nome="Sobremesas")
    massas = _categoria(nome="Massas")
    receita_sobremesa = _receita(titulo="Bolo", categoria=sobremesas, publicado=True)
    _receita(titulo="Lasanha", categoria=massas, publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"categoria": sobremesas.slug})

    titulos = [r.titulo for r in resposta.context["receitas"]]
    assert titulos == [receita_sobremesa.titulo]


def test_filtro_por_categoria_inexistente_retorna_lista_vazia(client: Client) -> None:
    """Slug sem correspondência é resultado vazio, não erro (RNF-02)."""
    _receita(publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"categoria": "nao-existe"})

    assert resposta.status_code == 200
    assert list(resposta.context["receitas"]) == []


def test_filtro_por_tag_existente(client: Client) -> None:
    tag_vegana = _tag(nome="vegana")
    com_tag = _receita(titulo="Receita vegana", publicado=True)
    com_tag.tags.add(tag_vegana)
    _receita(titulo="Receita comum", publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"tag": tag_vegana.slug})

    titulos = [r.titulo for r in resposta.context["receitas"]]
    assert titulos == [com_tag.titulo]


def test_filtro_por_tag_inexistente_retorna_lista_vazia(client: Client) -> None:
    _receita(publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"tag": "nao-existe"})

    assert resposta.status_code == 200
    assert list(resposta.context["receitas"]) == []


def test_busca_e_categoria_combinam_com_e_logico(client: Client) -> None:
    """Busca + categoria aplicam interseção, não união (RF-04)."""
    sobremesas = _categoria(nome="Sobremesas")
    massas = _categoria(nome="Massas")
    # ingredientes explícitos: o default do builder já contém "cenoura",
    # o que contaminaria justamente o cenário que este teste quer excluir.
    alvo = _receita(titulo="Bolo de cenoura", categoria=sobremesas, publicado=True)
    _receita(
        titulo="Lasanha de cenoura",
        categoria=massas,
        ingredientes="massa, molho, queijo",
        publicado=True,
    )
    _receita(
        titulo="Bolo de chocolate",
        categoria=sobremesas,
        ingredientes="chocolate, farinha, ovos",
        publicado=True,
    )

    resposta = client.get(
        reverse("receitas:lista"), {"q": "cenoura", "categoria": sobremesas.slug}
    )

    titulos = [r.titulo for r in resposta.context["receitas"]]
    assert titulos == [alvo.titulo]


def test_estado_vazio_mostra_mensagem_com_termo_buscado(client: Client) -> None:
    resposta = client.get(reverse("receitas:lista"), {"q": "abobora"})

    assert "Nenhuma receita encontrada" in resposta.content.decode()
    assert "abobora" in resposta.content.decode()


def test_paginacao_preserva_filtro_de_categoria_na_querystring(client: Client) -> None:
    categoria = _categoria()
    for i in range(10):
        _receita(titulo=f"Receita {i}", categoria=categoria, publicado=True)

    resposta = client.get(reverse("receitas:lista"), {"categoria": categoria.slug})

    conteudo = resposta.content.decode()
    assert f"categoria={categoria.slug}" in conteudo


# -----------------------------------------------------------------------------
# Detalhe público (RF-03, RF-04)
# -----------------------------------------------------------------------------
def test_detalhe_receita_publicada_retorna_200_com_campos(client: Client) -> None:
    receita = _receita(publicado=True)

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert receita.titulo in conteudo
    assert "cenouras" in conteudo  # vem de `ingredientes`, via splitlines


def test_detalhe_receita_nao_publicada_retorna_404(client: Client) -> None:
    receita = _receita(publicado=False)

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert resposta.status_code == 404


def test_detalhe_slug_inexistente_retorna_404(client: Client) -> None:
    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": "nao-existe"}))

    assert resposta.status_code == 404


def test_detalhe_sem_autor_nao_quebra(client: Client) -> None:
    receita = _receita(publicado=True, autor=None)

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert resposta.status_code == 200
    assert "Autor removido" in resposta.content.decode()


# -----------------------------------------------------------------------------
# Modelo Comentario (RF-01)
# -----------------------------------------------------------------------------
def test_comentario_criado_com_os_campos_esperados() -> None:
    comentario = _comentario(texto="Muito bom!")

    assert comentario.aprovado is True
    assert comentario.criado_em is not None
    assert comentario.texto == "Muito bom!"


def test_excluir_receita_apaga_os_comentarios() -> None:
    """``on_delete=CASCADE``: comentário não sobrevive sem a receita (RF-01)."""
    receita = _receita(publicado=True)
    comentario = _comentario(receita=receita)

    receita.delete()

    assert not Comentario.objects.filter(pk=comentario.pk).exists()


def test_excluir_autor_do_comentario_preserva_o_comentario() -> None:
    """``on_delete=SET_NULL``, mesma política de ``Receita.autor`` (RF-01)."""
    autor = User.objects.create_user(
        username="comentarista", password="senha-forte-123"
    )
    comentario = _comentario(autor=autor)

    autor.delete()

    comentario.refresh_from_db()
    assert comentario.autor is None


# -----------------------------------------------------------------------------
# Exibição de comentários (RF-02)
# -----------------------------------------------------------------------------
def test_comentario_aprovado_aparece_na_pagina(client: Client) -> None:
    receita = _receita(publicado=True)
    comentario = _comentario(receita=receita, texto="Comentário visível")

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert comentario.texto in resposta.content.decode()


def test_comentarios_aparecem_do_mais_antigo_ao_mais_novo(client: Client) -> None:
    receita = _receita(publicado=True)
    primeiro = _comentario(receita=receita, texto="Primeiro comentário")
    segundo = _comentario(receita=receita, texto="Segundo comentário")

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    conteudo = resposta.content.decode()
    assert conteudo.index(primeiro.texto) < conteudo.index(segundo.texto)


def test_comentario_reprovado_nao_aparece_na_pagina(client: Client) -> None:
    """Também cobre RF-07: desmarcar ``aprovado`` some com o comentário público."""
    receita = _receita(publicado=True)
    comentario = _comentario(
        receita=receita, texto="Comentário escondido", aprovado=False
    )

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert comentario.texto not in resposta.content.decode()


def test_comentario_sem_autor_mostra_usuario_removido(client: Client) -> None:
    receita = _receita(publicado=True)
    _comentario(receita=receita, autor=None, texto="Comentário órfão")

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert "Usuário removido" in resposta.content.decode()


# -----------------------------------------------------------------------------
# Formulário condicional por autenticação (RF-03)
# -----------------------------------------------------------------------------
def test_formulario_de_comentario_aparece_para_autenticado(client: Client) -> None:
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert 'name="texto"' in resposta.content.decode()


def test_convite_de_login_aparece_para_anonimo(client: Client) -> None:
    receita = _receita(publicado=True)

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    conteudo = resposta.content.decode()
    assert 'name="texto"' not in conteudo
    url_esperada = (
        reverse("usuarios:entrar")
        + "?next="
        + reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    )
    assert url_esperada in conteudo


# -----------------------------------------------------------------------------
# Criação de comentário (RF-04, RF-05)
# -----------------------------------------------------------------------------
def test_post_valido_cria_comentario_e_redireciona(client: Client) -> None:
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Ficou incrível!", "carimbo_tempo": _carimbo_valido()},
        follow=True,
    )

    assert Comentario.objects.filter(receita=receita, texto="Ficou incrível!").exists()
    assert "Comentário publicado!" in resposta.content.decode()


def test_post_com_texto_vazio_nao_cria_comentario(client: Client) -> None:
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "   ", "carimbo_tempo": _carimbo_valido()},
        follow=True,
    )

    assert not Comentario.objects.filter(receita=receita).exists()
    assert "O comentário não pode ficar vazio." in resposta.content.decode()


# -----------------------------------------------------------------------------
# Login obrigatório para comentar (RF-06)
# -----------------------------------------------------------------------------
def test_post_anonimo_redireciona_para_login_com_next_da_receita(
    client: Client,
) -> None:
    receita = _receita(publicado=True)

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Tentando comentar sem login"},
    )

    url_receita = reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    assert resposta.status_code == 302
    assert resposta["Location"] == f"{reverse('usuarios:entrar')}?next={url_receita}"
    assert not Comentario.objects.filter(receita=receita).exists()


def test_login_apos_redirect_volta_para_a_receita(client: Client) -> None:
    receita = _receita(publicado=True)
    User.objects.create_user(username="leitor", password="senha-forte-123")

    resposta_anonima = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Tentando comentar sem login"},
    )
    resposta_login = client.post(
        resposta_anonima["Location"],
        {"username": "leitor", "password": "senha-forte-123"},
    )

    url_receita = reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    assert resposta_login.status_code == 302
    assert resposta_login["Location"] == url_receita


# -----------------------------------------------------------------------------
# Limite de comentários por IP (spec 006, RF-02, RNF-02)
# -----------------------------------------------------------------------------
def test_bloqueia_a_partir_do_sexto_comentario_no_mesmo_ip(client: Client) -> None:
    """5 comentários consomem o limite; o 6º não é persistido."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)
    for indice in range(5):
        client.post(
            reverse("receitas:comentar", kwargs={"slug": receita.slug}),
            {
                "texto": f"Comentário número {indice}",
                "carimbo_tempo": _carimbo_valido(),
            },
        )

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Este deveria ser bloqueado", "carimbo_tempo": _carimbo_valido()},
    )

    assert Comentario.objects.filter(receita=receita).count() == 5
    assert not Comentario.objects.filter(texto="Este deveria ser bloqueado").exists()
    assert resposta.status_code == 302


def test_dois_ips_nao_compartilham_o_limite_de_comentarios(client: Client) -> None:
    """O contador é por IP -- outro IP não é afetado pelas tentativas do primeiro."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)
    for indice in range(5):
        client.post(
            reverse("receitas:comentar", kwargs={"slug": receita.slug}),
            {
                "texto": f"Comentário número {indice}",
                "carimbo_tempo": _carimbo_valido(),
            },
            REMOTE_ADDR="10.0.0.1",
        )

    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Comentário de outro IP", "carimbo_tempo": _carimbo_valido()},
        REMOTE_ADDR="10.0.0.2",
    )

    assert Comentario.objects.filter(texto="Comentário de outro IP").exists()


# -----------------------------------------------------------------------------
# Honeypot e time-trap (spec 007, RF-01, RF-02, RF-03, RNF-03)
# -----------------------------------------------------------------------------
def test_honeypot_preenchido_nao_cria_comentario_mas_finge_sucesso(
    client: Client,
) -> None:
    """Bot que preenche o campo-armadilha recebe a mesma resposta de sucesso."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {
            "texto": "Comentário de bot",
            "endereco_web": "http://spam.exemplo.com",
            "carimbo_tempo": _carimbo_valido(),
        },
        follow=True,
    )

    assert not Comentario.objects.filter(receita=receita).exists()
    assert "Comentário publicado!" in resposta.content.decode()


def test_carimbo_recente_demais_bloqueia_o_envio(client: Client) -> None:
    """POST enviado rápido demais depois do GET é tratado como bot."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Muito rápido", "carimbo_tempo": _carimbo_valido(segundos_atras=0)},
        follow=True,
    )

    assert not Comentario.objects.filter(receita=receita).exists()
    assert "Comentário publicado!" in resposta.content.decode()


def test_carimbo_ausente_ou_adulterado_e_tratado_como_suspeito(client: Client) -> None:
    """Sem carimbo ou com um valor forjado, o envio é tratado como bot."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Sem carimbo", "carimbo_tempo": "valor-forjado"},
        follow=True,
    )

    assert not Comentario.objects.filter(receita=receita).exists()
    assert "Comentário publicado!" in resposta.content.decode()


def test_envio_humano_normal_ainda_cria_comentario(client: Client) -> None:
    """Honeypot vazio + tempo plausível: o comentário é criado normalmente."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)

    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Comentário humano de verdade", "carimbo_tempo": _carimbo_valido()},
    )

    assert Comentario.objects.filter(
        receita=receita, texto="Comentário humano de verdade"
    ).exists()


def test_envio_bloqueado_por_antibot_nao_consome_o_limite_de_taxa(
    client: Client,
) -> None:
    """5 envios pegos pelo honeypot não esgotam o limite de taxa da spec 006."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)
    for _ in range(5):
        client.post(
            reverse("receitas:comentar", kwargs={"slug": receita.slug}),
            {
                "texto": "Bot",
                "endereco_web": "http://spam.exemplo.com",
                "carimbo_tempo": _carimbo_valido(),
            },
        )

    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {
            "texto": "Comentário humano depois dos bots",
            "carimbo_tempo": _carimbo_valido(),
        },
    )

    assert Comentario.objects.filter(
        receita=receita, texto="Comentário humano depois dos bots"
    ).exists()


# -----------------------------------------------------------------------------
# Moderação no admin (RF-07)
# -----------------------------------------------------------------------------
def test_listagem_do_admin_de_comentarios_responde_200(client: Client) -> None:
    staff = User.objects.create_user(
        username="admin-teste",
        password="senha-forte-123",
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(staff)
    _comentario()

    resposta = client.get("/admin/receitas/comentario/")

    assert resposta.status_code == 200
