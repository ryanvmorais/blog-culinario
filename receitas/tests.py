"""
Testes do domínio de receitas: models (spec 001), views públicas de
listagem/detalhe (spec 002), comentários (spec 005), limite de taxa (spec
006) e honeypot/time-trap (spec 007) na criação de comentário.

Estratégia de isolamento: tudo aqui é ORM/HTTP de teste do Django rodando
contra o banco de teste do pytest-django (``@pytest.mark.django_db``) — sem
mock. Não há I/O externo (rede, storage remoto) neste domínio ainda; o
upload de imagem usa ``SimpleUploadedFile``, e a capa salva vai para o
``MEDIA_ROOT`` temporário do ``conftest.py``. O cache é limpo antes
de cada teste (fixture autouse) para os contadores de limitação de taxa não
vazarem de um teste para o outro.
"""

from __future__ import annotations

import re
import time
from datetime import timedelta
from pathlib import Path
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
from pytest_django.fixtures import Settings

from .forms import _ASSINATURA_SALT, TAMANHO_MAXIMO_COMENTARIO
from .models import Categoria, Comentario, Receita, Tag

pytestmark = pytest.mark.django_db

User = get_user_model()

# A mensagem inteira, com o nível: o falso sucesso do honeypot e do time-trap só
# engana o robô se sair igual ao sucesso de verdade (spec 007, ADR-4).
_MENSAGEM_DE_SUCESSO = (
    '<p class="mensagem mensagem--success" tabindex="-1" autofocus>'
    "Comentário publicado!</p>"
)


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


def test_salvar_de_novo_mantem_o_slug() -> None:
    """Editar o nome no Admin não troca o endereço: o slug nasce uma vez só."""
    categoria = _categoria(nome="Doces")
    tag = _tag(nome="vegana")
    receita = _receita(titulo="Bolo de cenoura", categoria=categoria)

    categoria.nome, tag.nome, receita.titulo = "Doces finos", "vegano", "Bolo da vó"
    for objeto in (categoria, tag, receita):
        objeto.save()
        objeto.refresh_from_db()

    assert (categoria.slug, tag.slug, receita.slug) == (
        "doces",
        "vegana",
        "bolo-de-cenoura",
    )


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
# Categorias com receitas publicadas (spec 012, RF-06, ADR-2)
# -----------------------------------------------------------------------------
def test_com_receitas_publicadas_conta_so_as_publicadas() -> None:
    massas = _categoria(nome="Massas")
    _receita(categoria=massas, publicado=True)
    _receita(categoria=massas, publicado=False)

    (categoria,) = Categoria.objects.com_receitas_publicadas()

    assert categoria == massas
    # O atributo nasce do annotate(); o mypy só conhece os campos do modelo.
    assert categoria.total_receitas == 1  # type: ignore[attr-defined]


def test_com_receitas_publicadas_deixa_de_fora_categoria_so_com_rascunho() -> None:
    _receita(categoria=_categoria(nome="Rascunhos"), publicado=False)
    _categoria(nome="Vazia")

    assert list(Categoria.objects.com_receitas_publicadas()) == []


def test_com_receitas_publicadas_ordena_pela_contagem_e_pelo_nome() -> None:
    """Mais receitas primeiro; no empate, ordem alfabética."""
    # Massas nasce antes de Lanches: no empate, a ordem do banco (pk) daria
    # Massas primeiro, e só o desempate pelo nome põe Lanches na frente.
    sobremesas = _categoria(nome="Sobremesas")
    massas = _categoria(nome="Massas")
    lanches = _categoria(nome="Lanches")
    for _ in range(2):
        _receita(categoria=sobremesas, publicado=True)
    _receita(categoria=massas, publicado=True)
    _receita(categoria=lanches, publicado=True)

    nomes = [c.nome for c in Categoria.objects.com_receitas_publicadas()]

    assert nomes == ["Sobremesas", "Lanches", "Massas"]


# -----------------------------------------------------------------------------
# Validação de imagem de capa (RF-04)
# -----------------------------------------------------------------------------
def test_imagem_no_limite_de_5_mb_e_aceita() -> None:
    """5 MB exatos passam: o teto é inclusivo (o par do teste de um byte acima)."""
    capa = SimpleUploadedFile(
        "capa.jpg", b"0" * (5 * 1024 * 1024), content_type="image/jpeg"
    )

    _receita(imagem_capa=capa).full_clean()  # não deve levantar


def test_imagem_muito_grande_e_rejeitada() -> None:
    arquivo_grande = SimpleUploadedFile(
        "capa.jpg",
        b"0" * (5 * 1024 * 1024 + 1),
        content_type="image/jpeg",
    )
    receita = _receita(imagem_capa=arquivo_grande)

    with pytest.raises(ValidationError) as erro:
        receita.full_clean()
    assert erro.value.message_dict == {
        "imagem_capa": ["A imagem deve ter no máximo 5 MB."]
    }


@pytest.mark.parametrize("nome", ["capa.jpg", "capa.jpeg", "capa.png", "capa.webp"])
def test_extensao_de_imagem_permitida_e_aceita(nome: str) -> None:
    """Uma por extensão da lista: tirar qualquer uma recusaria a capa (RF-04)."""
    capa = SimpleUploadedFile(nome, b"0", content_type="application/octet-stream")

    _receita(imagem_capa=capa).full_clean()  # não deve levantar


@pytest.mark.parametrize("nome", ["capa.txt", "capa.gif", "capa.jpg.txt"])
def test_extensao_de_imagem_invalida_e_rejeitada(nome: str) -> None:
    arquivo_invalido = SimpleUploadedFile(
        nome,
        b"nao e uma imagem",
        content_type="text/plain",
    )
    receita = _receita(imagem_capa=arquivo_invalido)

    with pytest.raises(ValidationError) as erro:
        receita.full_clean()
    assert list(erro.value.message_dict) == ["imagem_capa"]


def test_capa_salva_nos_testes_fica_fora_da_media_do_projeto(tmp_path: Path) -> None:
    """A capa salva no teste vai para a pasta temporária, não para a ``media/``."""
    capa = SimpleUploadedFile("capa.jpg", b"0", content_type="image/jpeg")

    receita = _receita(imagem_capa=capa)

    assert Path(receita.imagem_capa.path).is_relative_to(tmp_path)


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
        reverse("admin:receitas_categoria_changelist"),
        reverse("admin:receitas_tag_changelist"),
        reverse("admin:receitas_receita_changelist"),
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
    # prefetch de tags + 1 das categorias do rodapé (spec 012, ADR-3) + 1 das
    # pílulas (spec 012, adendo, RF-26) — não cresce com o número de receitas
    # nem de tags.
    with django_assert_num_queries(5):
        client.get(reverse("receitas:lista"))


# -----------------------------------------------------------------------------
# Busca e filtros (RF-01 a RF-06, RNF-02)
# -----------------------------------------------------------------------------
def test_busca_por_titulo_encontra_receita(client: Client) -> None:
    """O termo "cenoura" só aparece no título (o par do teste por ingrediente)."""
    receita = _receita(
        titulo="Bolo de cenoura", ingredientes="farinha\novos", publicado=True
    )

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
    # O estado vazio do filtro, não o do blog sem receitas.
    assert "Nenhuma receita encontrada" in resposta.content.decode()


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
    # O estado vazio do filtro, não o do blog sem receitas.
    assert "Nenhuma receita encontrada" in resposta.content.decode()


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


@pytest.mark.parametrize(
    "parametros",
    [{"q": "  cenoura  "}, {"categoria": " doces "}, {"tag": " vegana "}],
    ids=["busca", "categoria", "tag"],
)
def test_espacos_nas_pontas_do_filtro_sao_ignorados(
    client: Client, parametros: dict[str, str]
) -> None:
    """Um filtro colado com espaço acha o mesmo que sem ele (RF-01 a RF-03)."""
    alvo = _receita(
        titulo="Bolo de cenoura", categoria=_categoria(nome="Doces"), publicado=True
    )
    alvo.tags.add(_tag(nome="vegana"))
    _receita(
        titulo="Lasanha",
        categoria=_categoria(nome="Massas"),
        ingredientes="massa, molho",
        publicado=True,
    )

    resposta = client.get(reverse("receitas:lista"), parametros)

    assert [r.titulo for r in resposta.context["receitas"]] == ["Bolo de cenoura"]


def test_busca_com_resultado_diz_o_termo_e_oferece_limpar(client: Client) -> None:
    """Só com a busca ativa, a abertura diz o termo, como na categoria (RF-13)."""
    _receita(titulo="Bolo de cenoura", publicado=True)

    html = client.get(reverse("receitas:lista"), {"q": "cenoura"}).content.decode()

    assert 'para <strong>"cenoura"</strong>' in html
    assert "Limpar filtro" in html


def _trecho(html: str, inicio: str, fim: str) -> str:
    """
    Recorta o HTML entre a primeira ocorrência de ``inicio`` e o ``fim`` seguinte.

    Args:
        html (str): a página inteira.
        inicio (str): marca onde o recorte começa.
        fim (str): marca onde o recorte termina, procurada depois do início.

    Returns:
        str: o pedaço do HTML, sem a marca final.
    """
    comeco = html.index(inicio)
    return html[comeco : html.index(fim, comeco)]


def test_estado_vazio_mostra_mensagem_com_termo_buscado(client: Client) -> None:
    resposta = client.get(reverse("receitas:lista"), {"q": "abobora"})

    # Só o parágrafo do estado vazio: o campo de busca também ecoa o termo.
    vazio = _trecho(resposta.content.decode(), '<p class="estado-vazio">', "<a ")
    assert " ".join(vazio.split()) == (
        '<p class="estado-vazio"> Nenhuma receita encontrada para "abobora".'
    )
    # Sem resultado, a abertura não diz "0 receitas": o estado vazio já diz.
    assert "Limpar filtro" not in resposta.content.decode()


def test_paginacao_preserva_filtro_de_categoria_na_querystring(client: Client) -> None:
    categoria = _categoria()
    for i in range(10):
        _receita(titulo=f"Receita {i}", categoria=categoria, publicado=True)
    lista = reverse("receitas:lista")

    primeira = client.get(lista, {"categoria": categoria.slug}).content.decode()
    segunda = client.get(lista, {"categoria": categoria.slug, "page": "2"})

    # Dentro da paginação: as pílulas e os cartões também levam ?categoria=.
    proxima = _trecho(primeira, '<nav class="paginacao', "</nav>")
    anterior = _trecho(segunda.content.decode(), '<nav class="paginacao', "</nav>")
    assert f'href="?page=2&categoria={categoria.slug}"' in proxima
    assert f'href="?page=1&categoria={categoria.slug}"' in anterior


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
    # O segundo nasce depois e o primeiro tem a data recuada: no mesmo tick do
    # relógio as duas empatariam, e a ordem invertida passaria pela ordem do pk.
    segundo = _comentario(receita=receita, texto="Segundo comentário")
    primeiro = _comentario(receita=receita, texto="Primeiro comentário")
    Comentario.objects.filter(pk=primeiro.pk).update(
        criado_em=timezone.now() - timedelta(days=1)
    )

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

    # O autor é nulo no modelo (SET_NULL): sem conferir, a view que esquecesse o
    # request.user gravaria um comentário "Usuário removido".
    (comentario,) = Comentario.objects.filter(receita=receita)
    assert comentario.texto == "Ficou incrível!"
    assert comentario.autor == autor
    assert _MENSAGEM_DE_SUCESSO in resposta.content.decode()


def test_post_em_receita_rascunho_responde_404_e_nao_grava(client: Client) -> None:
    """O slug de um rascunho não aceita comentário, mesmo com o envio válido."""
    receita = _receita(publicado=False)
    client.force_login(User.objects.create_user(username="leitor", password="x"))

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Comentário num rascunho", "carimbo_tempo": _carimbo_valido()},
    )

    assert resposta.status_code == 404
    assert not Comentario.objects.exists()


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
    assert (
        'class="mensagem mensagem--error" tabindex="-1" autofocus>'
        "O comentário não pode ficar vazio.</p>"
    ) in resposta.content.decode()


# -----------------------------------------------------------------------------
# Tamanho máximo do comentário (adendo, RF-08)
# -----------------------------------------------------------------------------
def _comentar(client: Client, receita: Receita, texto: str) -> str:
    """
    Envia um comentário como um leitor logado e devolve a página final.

    Args:
        client (Client): cliente de teste.
        receita (Receita): receita comentada.
        texto (str): texto do comentário.

    Returns:
        str: o HTML da página da receita depois do redirecionamento.
    """
    client.force_login(User.objects.create_user(username="leitor", password="x"))
    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": texto, "carimbo_tempo": _carimbo_valido()},
        follow=True,
    )
    return resposta.content.decode()


def test_campo_de_comentario_limita_no_navegador(client: Client) -> None:
    """O <textarea> sai com o maxlength, e o navegador não deixa passar dele."""
    receita = _receita(publicado=True)
    client.force_login(User.objects.create_user(username="leitor", password="x"))

    resposta = client.get(reverse("receitas:detalhe", kwargs={"slug": receita.slug}))

    assert f'maxlength="{TAMANHO_MAXIMO_COMENTARIO}"' in resposta.content.decode()


def test_comentario_no_limite_e_aceito(client: Client) -> None:
    """2.000 caracteres exatos passam: o limite é inclusivo."""
    receita = _receita(publicado=True)

    _comentar(client, receita, "a" * TAMANHO_MAXIMO_COMENTARIO)

    assert Comentario.objects.filter(receita=receita).count() == 1


@pytest.mark.parametrize("modo_demonstracao", [False, True])
def test_comentario_longo_demais_e_recusado(
    client: Client, settings: Settings, modo_demonstracao: bool
) -> None:
    """Um caractere além do limite: nada gravado e a mensagem própria."""
    settings.MODO_DEMONSTRACAO = modo_demonstracao
    receita = _receita(publicado=True)

    html = _comentar(client, receita, "a" * (TAMANHO_MAXIMO_COMENTARIO + 1))

    assert not Comentario.objects.filter(receita=receita).exists()
    assert "O comentário pode ter até 2.000 caracteres." in html


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
        follow=True,
    )

    assert Comentario.objects.filter(receita=receita).count() == 5
    assert not Comentario.objects.filter(texto="Este deveria ser bloqueado").exists()
    assert resposta.redirect_chain == [
        (reverse("receitas:detalhe", kwargs={"slug": receita.slug}), 302)
    ]
    # As 5 mensagens de sucesso anteriores ainda estão na fila (os envios não
    # seguiram o redirect); o foco fica na primeira, e esta vem por último.
    assert (
        '<p class="mensagem mensagem--error">'
        "Você está comentando rápido demais. Aguarde um instante.</p>"
    ) in resposta.content.decode()


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
    assert _MENSAGEM_DE_SUCESSO in resposta.content.decode()


def test_honeypot_so_com_espacos_nao_e_robo(client: Client) -> None:
    """O autopreenchimento que deixa um espaço no campo oculto não barra o leitor."""
    receita = _receita(publicado=True)
    client.force_login(User.objects.create_user(username="leitor", password="x"))

    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {
            "texto": "Com o campo oculto em branco",
            "endereco_web": "   ",
            "carimbo_tempo": _carimbo_valido(),
        },
    )

    assert Comentario.objects.filter(receita=receita).exists()


def test_campo_armadilha_fica_fora_do_tab_do_autopreenchimento_e_do_leitor(
    client: Client,
) -> None:
    """O teclado, o gerenciador de senhas e o leitor de tela pulam o campo."""
    receita = _receita(publicado=True)
    client.force_login(User.objects.create_user(username="leitor", password="x"))

    html = client.get(
        reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    ).content.decode()

    armadilha = _trecho(html, '<div class="campo-armadilha"', "</div>")
    assert armadilha.startswith('<div class="campo-armadilha" aria-hidden="true">')
    (campo,) = re.findall(r'<input [^>]*name="endereco_web"[^>]*>', armadilha)
    assert 'tabindex="-1"' in campo
    assert 'autocomplete="off"' in campo


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
    assert _MENSAGEM_DE_SUCESSO in resposta.content.decode()


def test_carimbo_servido_pela_pagina_deixa_o_leitor_comentar(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O carimbo do formulário volta no POST e, 2 s depois, o comentário entra."""
    # Os outros testes montam o carimbo à mão; sem este, a página que deixasse de
    # servi-lo faria todo leitor real cair no time-trap, com o falso sucesso.
    relogio = [1_800_000_000.0]
    monkeypatch.setattr(time, "time", lambda: relogio[0])
    receita = _receita(publicado=True)
    client.force_login(User.objects.create_user(username="leitor", password="x"))
    html = client.get(
        reverse("receitas:detalhe", kwargs={"slug": receita.slug})
    ).content.decode()
    (carimbo,) = re.findall(r'name="carimbo_tempo" value="([^"]+)"', html)

    relogio[0] += 2
    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {"texto": "Pelo formulário de verdade", "carimbo_tempo": carimbo},
    )

    assert Comentario.objects.filter(
        receita=receita, texto="Pelo formulário de verdade"
    ).exists()


@pytest.mark.parametrize(("decorridos", "grava"), [(1.999, False), (2.0, True)])
def test_tempo_minimo_do_envio_e_de_2_segundos(
    client: Client, monkeypatch: pytest.MonkeyPatch, decorridos: float, grava: bool
) -> None:
    """Abaixo de 2 s é robô; com 2 s exatos, o comentário entra (spec 007, RF-02)."""
    # Relógio parado: com o tempo real, o envio "de 2 s" chegaria com 2,00x s e
    # passaria também numa comparação que recusasse os 2 s exatos.
    agora = 1_800_000_000.0
    monkeypatch.setattr(time, "time", lambda: agora)
    receita = _receita(publicado=True)
    client.force_login(User.objects.create_user(username="leitor", password="x"))

    client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        {
            "texto": "No limite do relógio",
            "carimbo_tempo": signing.dumps(agora - decorridos, salt=_ASSINATURA_SALT),
        },
    )

    assert Comentario.objects.filter(receita=receita).exists() is grava


@pytest.mark.parametrize(
    "carimbo",
    [
        None,
        "valor-forjado",
        signing.dumps(time.time() - 60, salt="outra.parte.do.projeto"),
        signing.dumps(time.time() - 60),
    ],
    ids=["ausente", "forjado", "outro-salt", "sem-salt"],
)
def test_carimbo_ausente_ou_adulterado_e_tratado_como_suspeito(
    client: Client, carimbo: str | None
) -> None:
    """Sem carimbo, forjado ou assinado fora do formulário: o envio é de bot (ADR-2)."""
    receita = _receita(publicado=True)
    autor = User.objects.create_user(username="leitor", password="senha-forte-123")
    client.force_login(autor)
    dados = {"texto": "Sem carimbo válido"}
    if carimbo is not None:
        dados["carimbo_tempo"] = carimbo

    resposta = client.post(
        reverse("receitas:comentar", kwargs={"slug": receita.slug}),
        dados,
        follow=True,
    )

    assert not Comentario.objects.filter(receita=receita).exists()
    assert _MENSAGEM_DE_SUCESSO in resposta.content.decode()


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

    resposta = client.get(reverse("admin:receitas_comentario_changelist"))

    assert resposta.status_code == 200
