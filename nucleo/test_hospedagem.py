"""
Testes da hospedagem na Railway (spec 011).

Cobrem a receita de build (``railpack.json``) e as configurações de produção que
o serviço carrega ao subir.

Estratégia de isolamento: as configurações de produção são lidas num processo à
parte (``subprocess``), com o ambiente montado pelo teste, porque o pacote de
configurações lê o ambiente ao ser importado e recarregá-lo dentro do pytest
deixaria o ambiente de um teste para os outros. Toda variável do projeto vai
explícita no ambiente do processo filho, vazia quando o teste não a usa: o
``.env`` local só preenche o que falta, então não interfere. Sem rede.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.http import HttpRequest
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from PIL import Image

from blog_culinario.cache import NOME_ARQUIVO_TRAVA, CacheArquivoAtomico
from blog_culinario.limitacao import limite_excedido
from blog_culinario.origem import ip_do_visitante, trava_de_origem_ligada

BASE_DIR: Path = settings.BASE_DIR

# Variáveis que o pacote de configurações lê. O processo filho recebe todas,
# vazias por padrão, para o .env de quem roda os testes não entrar no resultado.
VARIAVEIS_DO_PROJETO = (
    "DJANGO_SETTINGS_MODULE",
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "ADMIN_URL",
    "MODO_DEMONSTRACAO",
    "URL_PUBLICA",
    "DIRETORIO_DADOS",
    "ORIGEM_SEGREDO",
    "ORIGEM_SEGREDO_ANTERIOR",
)

# Domínio de exemplo do serviço atrás do proxy, nos testes de HTTPS e de CSRF.
HOST_PUBLICO = "blog.exemplo.com.br"

# Ambiente mínimo com que as configurações de produção sobem.
AMBIENTE_PRODUCAO: dict[str, str | None] = {
    "DJANGO_SETTINGS_MODULE": "blog_culinario.settings.prod",
    "SECRET_KEY": "chave-de-teste-" + "x" * 50,
    "ALLOWED_HOSTS": "blog.exemplo.com.br",
}


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------


def _rodar_python(
    codigo: str, ambiente: dict[str, str | None], *argumentos: str
) -> subprocess.CompletedProcess[str]:
    """
    Roda um trecho de Python num processo novo, na raiz do projeto.

    Args:
        codigo (str): código passado ao ``python -c``; ignorado quando
            ``argumentos`` traz um script (``manage.py``).
        ambiente (dict[str, str | None]): variáveis do projeto para o processo
            filho; as que faltarem vão vazias, e as marcadas com ``None`` ficam
            fora do ambiente (variável ausente, não vazia).
        *argumentos (str): no lugar de ``-c codigo``, os argumentos do Python
            (ex.: ``"manage.py", "check", "--deploy"``).

    Returns:
        subprocess.CompletedProcess[str]: código de saída, ``stdout`` e
        ``stderr`` do processo, em texto.
    """
    env = {k: v for k, v in os.environ.items() if k not in VARIAVEIS_DO_PROJETO}
    env.update(dict.fromkeys(VARIAVEIS_DO_PROJETO, ""))
    for nome, valor in ambiente.items():
        if valor is None:
            env.pop(nome, None)
        else:
            env[nome] = valor
    # Saída em UTF-8 também no Windows, para as mensagens em português.
    env["PYTHONUTF8"] = "1"
    comando = [sys.executable, *(argumentos or ("-c", codigo))]
    return subprocess.run(
        comando,
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _configuracoes(ambiente: dict[str, str | None], *nomes: str) -> dict[str, Any]:
    """
    Lê configurações do Django num processo novo, com o ambiente pedido.

    Args:
        ambiente (dict[str, str | None]): variáveis do projeto (ver
            ``_rodar_python``).
        *nomes (str): nomes das configurações a ler; a que não existe volta
            como ``None``.

    Returns:
        dict[str, Any]: cada nome com o valor lido, convertido para JSON
        (caminhos viram texto, tuplas viram listas).
    """
    codigo = (
        "import json\n"
        "from django.conf import settings\n"
        f"nomes = {list(nomes)!r}\n"
        "print(json.dumps({n: getattr(settings, n, None) for n in nomes},"
        " default=str))\n"
    )
    resultado = _rodar_python(codigo, ambiente)
    assert resultado.returncode == 0, resultado.stderr
    valores: dict[str, Any] = json.loads(resultado.stdout.strip().splitlines()[-1])
    return valores


# ---------------------------------------------------------------------------
# Receita de build (RF-01, RF-02)
# ---------------------------------------------------------------------------


def _receita_de_build() -> dict[str, Any]:
    """
    Lê o ``railpack.json`` da raiz.

    Returns:
        dict[str, Any]: o conteúdo do arquivo.
    """
    conteudo: dict[str, Any] = json.loads(
        (BASE_DIR / "railpack.json").read_text(encoding="utf-8")
    )
    return conteudo


def test_build_instala_pelo_lock_sem_dev_e_com_o_extra_prod() -> None:
    comandos = _receita_de_build()["steps"]["build"]["commands"]
    instalacao = comandos[0]
    assert instalacao.startswith("uv sync")
    for opcao in ("--locked", "--no-dev", "--extra prod"):
        assert opcao in instalacao


def test_collectstatic_roda_no_build_com_as_configuracoes_de_producao() -> None:
    # Só as configurações de produção gravam o manifesto do WhiteNoise; sem ele,
    # toda página com estático responde 500.
    comandos = _receita_de_build()["steps"]["build"]["commands"]
    collectstatic = [c for c in comandos if "collectstatic" in c]
    assert len(collectstatic) == 1
    assert "DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod" in collectstatic[0]
    assert "--noinput" in collectstatic[0]


def test_start_migra_antes_do_gunicorn_na_porta_da_plataforma() -> None:
    inicio = _receita_de_build()["deploy"]["startCommand"]
    assert "export DJANGO_SETTINGS_MODULE=blog_culinario.settings.prod &&" in inicio
    assert "migrate --noinput &&" in inicio
    assert inicio.index("migrate") < inicio.index("gunicorn")
    assert "gunicorn blog_culinario.wsgi:application" in inicio
    assert "--bind 0.0.0.0:${PORT:-8000}" in inicio


def test_wsgi_sem_a_variavel_carrega_as_configuracoes_de_producao() -> None:
    codigo = (
        "import os\n"
        "import blog_culinario.wsgi\n"
        "from django.conf import settings\n"
        "print(os.environ['DJANGO_SETTINGS_MODULE'], settings.DEBUG)\n"
    )
    ambiente = {**AMBIENTE_PRODUCAO, "DJANGO_SETTINGS_MODULE": None}
    resultado = _rodar_python(codigo, ambiente)
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.split() == ["blog_culinario.settings.prod", "False"]


def test_manage_py_segue_nas_configuracoes_de_desenvolvimento() -> None:
    manage = (BASE_DIR / "manage.py").read_text(encoding="utf-8")
    assert '"DJANGO_SETTINGS_MODULE", "blog_culinario.settings.dev"' in manage


# ---------------------------------------------------------------------------
# Configurações de produção (RF-05, RF-06, RF-11, RF-12)
# ---------------------------------------------------------------------------


def _env_local_define(nome: str) -> bool:
    """
    Diz se o ``.env`` da raiz define uma variável.

    O ``base.py`` lê o ``.env`` só para preencher o que falta no ambiente, então
    um teste de variável ausente não vale quando o ``.env`` a define.

    Args:
        nome (str): nome da variável.

    Returns:
        bool: ``True`` se há uma linha ``NOME=`` no ``.env``.
    """
    arquivo = BASE_DIR / ".env"
    if not arquivo.exists():
        return False
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    return any(linha.strip().startswith(f"{nome}=") for linha in linhas)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("exemplo.com, www.exemplo.com,", ["exemplo.com", "www.exemplo.com"]),
        ("  exemplo.com  ", ["exemplo.com"]),
        ("", []),
    ],
)
def test_allowed_hosts_sem_espacos_nem_itens_vazios(
    valor: str, esperado: list[str]
) -> None:
    ambiente = {**AMBIENTE_PRODUCAO, "ALLOWED_HOSTS": valor}
    assert _configuracoes(ambiente, "ALLOWED_HOSTS")["ALLOWED_HOSTS"] == esperado


def test_allowed_hosts_ausente_derruba_a_subida() -> None:
    if _env_local_define("ALLOWED_HOSTS"):
        pytest.skip("o .env local define ALLOWED_HOSTS")
    ambiente = {**AMBIENTE_PRODUCAO, "ALLOWED_HOSTS": None}
    codigo = "from django.conf import settings\nsettings.DEBUG\n"
    resultado = _rodar_python(codigo, ambiente)
    assert resultado.returncode != 0
    assert "ImproperlyConfigured" in resultado.stderr
    assert "ALLOWED_HOSTS" in resultado.stderr


@pytest.mark.parametrize("modulo", ["prod", "dev"])
@pytest.mark.parametrize("valor", [None, ""])
def test_sem_chave_secreta_nenhum_ambiente_sobe(valor: str | None, modulo: str) -> None:
    # Nem o desenvolvimento tem chave fixa: ela valeria em todo clone (RF-15).
    if valor is None and _env_local_define("SECRET_KEY"):
        pytest.skip("o .env local define SECRET_KEY")
    ambiente = {
        **AMBIENTE_PRODUCAO,
        "DJANGO_SETTINGS_MODULE": f"blog_culinario.settings.{modulo}",
        "SECRET_KEY": valor,
    }
    codigo = "from django.conf import settings\nsettings.SECRET_KEY\n"
    resultado = _rodar_python(codigo, ambiente)
    assert resultado.returncode != 0
    assert "ImproperlyConfigured" in resultado.stderr
    assert "django-insecure" not in resultado.stdout


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (None, "admin/"),
        ("", "admin/"),
        ("/", "admin/"),
        ("painel-secreto/", "painel-secreto/"),
        (" /painel-secreto ", "painel-secreto/"),
    ],
)
def test_admin_url_normaliza_e_nunca_fica_vazio(
    valor: str | None, esperado: str
) -> None:
    # Vazio, o Admin tomaria a raiz no lugar da home (RF-14).
    if valor is None and _env_local_define("ADMIN_URL"):
        pytest.skip("o .env local define ADMIN_URL")
    ambiente = {**AMBIENTE_PRODUCAO, "ADMIN_URL": valor}
    assert _configuracoes(ambiente, "ADMIN_URL")["ADMIN_URL"] == esperado


def test_admin_responde_no_caminho_do_admin_url() -> None:
    codigo = (
        "import django\n"
        "django.setup()\n"
        "from django.urls import reverse\n"
        "print(reverse('admin:index'), reverse('nucleo:home'))\n"
    )
    ambiente = {**AMBIENTE_PRODUCAO, "ADMIN_URL": "painel-secreto/"}
    resultado = _rodar_python(codigo, ambiente)
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.split() == ["/painel-secreto/", "/"]


def test_sem_diretorio_de_dados_banco_e_midia_ficam_na_raiz() -> None:
    valores = _configuracoes(AMBIENTE_PRODUCAO, "DATABASES", "MEDIA_ROOT")
    assert Path(valores["DATABASES"]["default"]["NAME"]) == BASE_DIR / "db.sqlite3"
    assert Path(valores["MEDIA_ROOT"]) == BASE_DIR / "media"


def test_diretorio_de_dados_absoluto_leva_banco_e_midia(tmp_path: Path) -> None:
    ambiente = {**AMBIENTE_PRODUCAO, "DIRETORIO_DADOS": str(tmp_path)}
    valores = _configuracoes(ambiente, "DATABASES", "MEDIA_ROOT")
    assert Path(valores["DATABASES"]["default"]["NAME"]) == tmp_path / "db.sqlite3"
    assert Path(valores["MEDIA_ROOT"]) == tmp_path / "media"


def test_diretorio_de_dados_relativo_fica_dentro_da_raiz() -> None:
    ambiente = {**AMBIENTE_PRODUCAO, "DIRETORIO_DADOS": " dados "}
    valores = _configuracoes(ambiente, "MEDIA_ROOT")
    assert Path(valores["MEDIA_ROOT"]) == BASE_DIR / "dados" / "media"


def test_producao_le_o_proxy_registra_erros_e_silencia_o_mail_e001() -> None:
    nomes = ("SECURE_PROXY_SSL_HEADER", "LOGGING", "SILENCED_SYSTEM_CHECKS")
    valores = _configuracoes(AMBIENTE_PRODUCAO, *nomes)
    assert valores["SECURE_PROXY_SSL_HEADER"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert valores["LOGGING"]["root"] == {"handlers": ["console"], "level": "WARNING"}
    assert valores["LOGGING"]["loggers"]["django.request"]["level"] == "ERROR"
    assert valores["SILENCED_SYSTEM_CHECKS"] == ["mail.E001"]


def test_desenvolvimento_nao_le_o_proxy_nem_silencia_checagem() -> None:
    nomes = ("SECURE_PROXY_SSL_HEADER", "LOGGING", "SILENCED_SYSTEM_CHECKS")
    ambiente: dict[str, str | None] = {
        "DJANGO_SETTINGS_MODULE": "blog_culinario.settings.dev"
    }
    valores = _configuracoes(ambiente, *nomes)
    assert valores == {
        "SECURE_PROXY_SSL_HEADER": None,
        "LOGGING": {},
        "SILENCED_SYSTEM_CHECKS": [],
    }


def test_log_de_producao_mostra_o_500_e_esconde_o_404() -> None:
    # O django.setup() aplica o LOGGING do prod.py; o 500 sai como ERROR e o 404
    # como WARNING no django.request.
    codigo = (
        "import logging, django\n"
        "django.setup()\n"
        "logger = logging.getLogger('django.request')\n"
        "logger.error('erro-de-servidor')\n"
        "logger.warning('pagina-nao-encontrada')\n"
    )
    resultado = _rodar_python(codigo, AMBIENTE_PRODUCAO)
    assert resultado.returncode == 0, resultado.stderr
    assert "erro-de-servidor" in resultado.stderr
    assert "pagina-nao-encontrada" not in resultado.stderr


def test_check_deploy_sem_erro_nem_aviso(tmp_path: Path) -> None:
    # A checagem de cache do Django cria a pasta do cache: fica no tmp_path.
    ambiente = {**AMBIENTE_PRODUCAO, "DIRETORIO_DADOS": str(tmp_path)}
    resultado = _rodar_python("", ambiente, "manage.py", "check", "--deploy")
    saida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 0, saida
    # O mail.E001 fica silenciado no prod.py: o blog não envia e-mail.
    assert re.findall(r"\((\w+\.[EWCI]\d+)\)", saida) == []


# ---------------------------------------------------------------------------
# HTTPS e CSRF atrás do proxy (RF-03, RF-04)
# ---------------------------------------------------------------------------

# O que o prod.py liga para rodar atrás do proxy, aplicado nas configurações
# de desenvolvimento da suíte: assim o teste vê o redirect, o cookie Secure e o
# X-Forwarded-Proto sem subir as configurações de produção.
ATRAS_DO_PROXY = override_settings(
    ALLOWED_HOSTS=[HOST_PUBLICO],
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)


@ATRAS_DO_PROXY
@pytest.mark.django_db
def test_pedido_https_pelo_proxy_nao_redireciona_e_o_cookie_e_seguro() -> None:
    resposta = Client().get(reverse("usuarios:entrar"), headers=_cabecalhos())
    assert resposta.status_code == 200
    assert resposta.cookies["csrftoken"]["secure"] is True


@ATRAS_DO_PROXY
@pytest.mark.parametrize("protocolo", [None, "http"])
def test_pedido_http_redireciona_para_https(protocolo: str | None) -> None:
    cabecalhos = {"host": HOST_PUBLICO}
    if protocolo:
        cabecalhos["x-forwarded-proto"] = protocolo
    resposta = Client().get("/", headers=cabecalhos)
    assert resposta.status_code == 301
    assert resposta["Location"] == f"https://{HOST_PUBLICO}/"


def _cabecalhos(**extra: str) -> dict[str, str]:
    """
    Monta os cabeçalhos de um pedido HTTPS que chega pelo proxy.

    Args:
        **extra (str): cabeçalhos a mais (ex.: ``origin``).

    Returns:
        dict[str, str]: ``Host`` do domínio público, ``X-Forwarded-Proto: https``
        e os extras.
    """
    return {"host": HOST_PUBLICO, "x-forwarded-proto": "https", **extra}


def _post_do_login(origem: str) -> int:
    """
    Envia o login pelo proxy, com o token CSRF e o ``Origin`` pedido.

    Args:
        origem (str): valor do cabeçalho ``Origin``.

    Returns:
        int: o status da resposta ao POST.
    """
    cliente = Client(enforce_csrf_checks=True)
    url = reverse("usuarios:entrar")
    cliente.get(url, headers=_cabecalhos())
    token = cliente.cookies["csrftoken"].value
    resposta = cliente.post(
        url,
        {"username": "ninguem", "password": "errada", "csrfmiddlewaretoken": token},
        headers=_cabecalhos(origin=origem),
    )
    return resposta.status_code


@ATRAS_DO_PROXY
@pytest.mark.django_db
def test_post_com_origin_do_proprio_site_passa_pelo_csrf() -> None:
    # Login inválido volta 200 com o formulário: passou do CSRF, que daria 403.
    assert _post_do_login(f"https://{HOST_PUBLICO}") == 200


@ATRAS_DO_PROXY
@pytest.mark.django_db
def test_post_com_origin_de_outro_site_e_recusado() -> None:
    assert _post_do_login("https://atacante.exemplo") == 403


# ---------------------------------------------------------------------------
# Cache em arquivo e contagem atômica (RF-08)
# ---------------------------------------------------------------------------


def _cache_na_pasta(pasta: Path) -> CacheArquivoAtomico:
    """
    Cria uma instância do backend na pasta pedida, como cada worker cria a sua.

    Args:
        pasta (Path): pasta do cache.

    Returns:
        CacheArquivoAtomico: o backend, sem prefixo nem versão próprios.
    """
    return CacheArquivoAtomico(str(pasta), {})


def _validade_gravada(backend: CacheArquivoAtomico, chave: str) -> float:
    """
    Lê a validade que o ``FileBasedCache`` gravou no arquivo da chave.

    Args:
        backend (CacheArquivoAtomico): o backend que gravou a chave.
        chave (str): a chave.

    Returns:
        float: a validade, em segundos desde a época.
    """
    # _key_to_file é interno do FileBasedCache e não está nos stubs do Django.
    arquivo = backend._key_to_file(chave)  # type: ignore[attr-defined]
    with open(arquivo, "rb") as conteudo:
        validade: float = pickle.load(conteudo)
    return validade


def test_contagem_de_um_worker_aparece_no_outro(tmp_path: Path) -> None:
    worker_a, worker_b = _cache_na_pasta(tmp_path), _cache_na_pasta(tmp_path)
    assert worker_a.add("contador", 0, timeout=60) is True
    assert worker_b.add("contador", 0, timeout=60) is False
    assert worker_a.incr("contador") == 1
    assert worker_b.incr("contador") == 2
    assert worker_a.get("contador") == 2


def test_contagem_de_outro_processo_aparece(tmp_path: Path) -> None:
    backend = _cache_na_pasta(tmp_path)
    backend.add("contador", 0, timeout=60)
    backend.incr("contador")
    codigo = (
        "import sys\n"
        "from blog_culinario.cache import CacheArquivoAtomico\n"
        "print(CacheArquivoAtomico(sys.argv[1], {}).incr('contador'))\n"
    )
    resultado = _rodar_python(
        "",
        {"DJANGO_SETTINGS_MODULE": "blog_culinario.settings.dev"},
        "-c",
        codigo,
        str(tmp_path),
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "2"
    assert backend.get("contador") == 2


def test_incr_mantem_a_validade_da_chave(tmp_path: Path) -> None:
    # O incr() herdado regravaria com o TIMEOUT padrão (300 s) e a janela de 60 s
    # recomeçaria a cada tentativa.
    backend = _cache_na_pasta(tmp_path)
    backend.add("contador", 0, timeout=60)
    validade_original = _validade_gravada(backend, "contador")
    time.sleep(0.05)
    backend.incr("contador")
    assert abs(_validade_gravada(backend, "contador") - validade_original) < 0.01


def test_incr_de_chave_ausente_ou_expirada_levanta_value_error(tmp_path: Path) -> None:
    backend = _cache_na_pasta(tmp_path)
    with pytest.raises(ValueError):
        backend.incr("ausente")
    backend.set("expirada", 1, timeout=0)  # timeout 0 grava já expirada
    with pytest.raises(ValueError):
        backend.incr("expirada")


def test_clear_nao_apaga_a_trava(tmp_path: Path) -> None:
    backend = _cache_na_pasta(tmp_path)
    backend.add("contador", 0, timeout=60)
    backend.clear()
    assert (tmp_path / NOME_ARQUIVO_TRAVA).exists()
    assert backend.get("contador") is None


def test_tentativas_simultaneas_nao_passam_do_limite(rf: RequestFactory) -> None:
    # Cada thread recebe do Django a própria instância do cache, como cada worker
    # do gunicorn tem a sua; a barreira solta todas ao mesmo tempo.
    total, limite = 12, 5
    barreira = threading.Barrier(total)
    aceitas: list[bool] = []

    def tentar() -> None:
        pedido = rf.post("/", REMOTE_ADDR="203.0.113.7")
        barreira.wait()
        aceitas.append(not limite_excedido(pedido, "teste", limite, 60))

    threads = [threading.Thread(target=tentar) for _ in range(total)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert aceitas.count(True) == limite


# ---------------------------------------------------------------------------
# Trava de origem e IP do visitante (RF-09, RF-10, RF-11, RNF-05)
# ---------------------------------------------------------------------------

# Dois segredos ligados ao mesmo tempo, como durante a troca: o teste confere
# que os dois passam e que qualquer outro valor é recusado.
SEGREDO_ATUAL = "segredo-atual-de-teste"
SEGREDO_ANTERIOR = "segredo-anterior-de-teste"

COM_TRAVA = override_settings(ORIGEM_SEGREDOS=(SEGREDO_ATUAL, SEGREDO_ANTERIOR))


@pytest.mark.django_db
def test_sem_segredo_a_trava_fica_desligada() -> None:
    assert trava_de_origem_ligada() is False
    assert Client().get("/").status_code == 200


@COM_TRAVA
@pytest.mark.django_db
@pytest.mark.parametrize("valor", [None, "", "palpite-errado", SEGREDO_ATUAL + "x"])
def test_pedido_sem_o_segredo_e_recusado_com_a_pagina_403(
    valor: str | None, caplog: pytest.LogCaptureFixture
) -> None:
    cabecalhos = {} if valor is None else {"x-origin-verify": valor}
    with caplog.at_level(logging.WARNING, logger="blog_culinario.origem"):
        resposta = Client().get("/receitas/", headers=cabecalhos)
    assert resposta.status_code == 403
    assert "Erro 403" in resposta.content.decode()
    avisos = [r for r in caplog.records if r.name == "blog_culinario.origem"]
    assert len(avisos) == 1
    assert avisos[0].getMessage() == "pedido sem o segredo de origem: GET /receitas/"
    if valor:
        assert valor not in caplog.text


@COM_TRAVA
@pytest.mark.django_db
@pytest.mark.parametrize("valor", [SEGREDO_ATUAL, SEGREDO_ANTERIOR])
def test_pedido_com_o_segredo_atual_ou_anterior_passa(valor: str) -> None:
    resposta = Client().get("/", headers={"x-origin-verify": valor})
    assert resposta.status_code == 200


def _pedido(rf: RequestFactory, **meta: str) -> HttpRequest:
    """
    Monta um GET com o ``request.META`` pedido.

    Args:
        rf (RequestFactory): fábrica de pedidos do Django.
        **meta (str): chaves do ``request.META`` (``REMOTE_ADDR``,
            ``HTTP_CF_CONNECTING_IP``).

    Returns:
        HttpRequest: o pedido.
    """
    # O RequestFactory aceita chaves do request.META como kwargs, mas os stubs
    # tipam esses kwargs de forma mais estreita que str.
    pedido: HttpRequest = rf.get("/", **meta)  # type: ignore[arg-type]
    return pedido


@COM_TRAVA
@pytest.mark.parametrize(
    ("cf_ip", "esperado"),
    [
        ("198.51.100.20", "198.51.100.20"),
        (" 2001:db8::1 ", "2001:db8::1"),
        ("", "10.0.0.1"),
        ("nao-e-ip", "10.0.0.1"),
    ],
)
def test_com_a_trava_o_ip_vem_do_cf_connecting_ip(
    rf: RequestFactory, cf_ip: str, esperado: str
) -> None:
    pedido = _pedido(rf, REMOTE_ADDR="10.0.0.1", HTTP_CF_CONNECTING_IP=cf_ip)
    assert ip_do_visitante(pedido) == esperado


def test_sem_a_trava_o_cf_connecting_ip_do_cliente_e_ignorado(
    rf: RequestFactory,
) -> None:
    pedido = _pedido(rf, REMOTE_ADDR="10.0.0.1", HTTP_CF_CONNECTING_IP="198.51.100.20")
    assert ip_do_visitante(pedido) == "10.0.0.1"


@pytest.mark.parametrize("trava_ligada", [True, False])
def test_limite_separa_visitantes_so_com_a_trava(
    rf: RequestFactory, trava_ligada: bool
) -> None:
    # Dois visitantes atrás do mesmo proxy: com a trava, cada um tem o próprio
    # contador; sem ela, o segundo herda o limite esgotado pelo primeiro.
    segredos = (SEGREDO_ATUAL,) if trava_ligada else ()
    with override_settings(ORIGEM_SEGREDOS=segredos):
        for _ in range(5):
            primeiro = _pedido(
                rf, REMOTE_ADDR="10.0.0.1", HTTP_CF_CONNECTING_IP="198.51.100.1"
            )
            assert limite_excedido(primeiro, "teste", 5, 60) is False
        segundo = _pedido(
            rf, REMOTE_ADDR="10.0.0.1", HTTP_CF_CONNECTING_IP="198.51.100.2"
        )
        assert limite_excedido(segundo, "teste", 5, 60) is (not trava_ligada)


# ---------------------------------------------------------------------------
# Mídia com DEBUG=False (RF-07)
# ---------------------------------------------------------------------------


@pytest.fixture
def midia(settings: Any, tmp_path: Path) -> Path:
    """
    Põe o ``MEDIA_ROOT`` numa pasta temporária com uma capa e uma subpasta.

    Args:
        settings (Any): fixture do pytest-django que troca configurações.
        tmp_path (Path): pasta temporária do teste.

    Returns:
        Path: a pasta de mídia, com ``capas/bolo.jpg`` e a subpasta ``capas/``.
    """
    pasta = tmp_path / "media"
    (pasta / "capas").mkdir(parents=True)
    Image.new("RGB", (4, 4), "orange").save(pasta / "capas" / "bolo.jpg", "JPEG")
    settings.MEDIA_ROOT = pasta
    return pasta


@pytest.mark.django_db
def test_capa_servida_com_debug_desligado(midia: Path) -> None:
    resposta = Client().get("/media/capas/bolo.jpg")
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "image/jpeg"
    assert resposta["X-Content-Type-Options"] == "nosniff"
    assert "max-age=86400" in resposta["Cache-Control"]
    assert "public" in resposta["Cache-Control"]
    # O serve devolve um FileResponse, cujo streaming_content os stubs não
    # expõem no tipo genérico da resposta do Client.
    conteudo = b"".join(resposta.streaming_content)  # type: ignore[attr-defined]
    assert conteudo == (midia / "capas" / "bolo.jpg").read_bytes()


@pytest.mark.django_db
def test_capa_webp_sai_como_image_webp(midia: Path) -> None:
    # O Python 3.12 sem o mime.types do sistema não conhece o .webp.
    Image.new("RGB", (4, 4), "orange").save(midia / "capas" / "bolo.webp", "WEBP")
    resposta = Client().get("/media/capas/bolo.webp")
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "image/webp"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "caminho",
    [
        "/media/capas/nao-existe.jpg",
        "/media/capas/",
        "/media/capas",
        "/media/../conftest.py",
        "/media/capas/%2e%2e/%2e%2e/conftest.py",
    ],
)
def test_caminho_invalido_responde_404_sem_listar(midia: Path, caminho: str) -> None:
    resposta = Client().get(caminho)
    assert resposta.status_code == 404
    pagina = resposta.content.decode()
    assert "Erro 404" in pagina
    assert "bolo.jpg" not in pagina


@pytest.mark.django_db
def test_midia_so_aceita_get_e_head(midia: Path) -> None:
    assert Client().head("/media/capas/bolo.jpg").status_code == 200
    assert Client().post("/media/capas/bolo.jpg").status_code == 405


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_capa_segue_servida_com_debug_ligado(midia: Path) -> None:
    assert Client().get("/media/capas/bolo.jpg").status_code == 200
