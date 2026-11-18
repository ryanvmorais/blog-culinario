"""
Comando ``semear_dados_demo``: dados fictícios para auditar o site e desenvolver.

Um banco vazio dá páginas vazias e métricas enganosas, e a página de detalhe de uma
receita nem existe num banco novo. O Lighthouse CI
(``.github/workflows/lighthouse.yml``) roda este comando antes de subir o servidor;
a configuração dele
(``.github/lighthouse/``) cita o slug de uma das receitas daqui, e o
``receitas/test_semear_dados_demo.py`` confere que toda URL auditada responde 200.

O comando é idempotente (rodar duas vezes não duplica nada), recusa rodar com
``DEBUG=False`` (são dados de mentira, nunca de produção) e gera as imagens de capa
com o Pillow, para o CI não depender de rede nem de arquivos no repositório.

Uso::

    uv run python manage.py semear_dados_demo
"""

from __future__ import annotations

import io
from typing import Any, TypedDict

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageOps

from receitas.models import Categoria, Comentario, Receita, Tag

# -----------------------------------------------------------------------------
# Dados de demonstração
# -----------------------------------------------------------------------------
# Paleta (topo, base) dos gradientes que fazem as vezes de foto. Geradas aqui, com
# o Pillow, para o comando não depender de rede (o Lighthouse CI roda isolado).
CORES = [
    ("#d97706", "#451a03"),
    ("#be123c", "#4c0519"),
    ("#15803d", "#052e16"),
    ("#7c2d12", "#1c0a05"),
]

# Autor das receitas e dos comentários. A senha é descartável: o banco de demonstração
# vive só no CI ou na máquina de quem rodou o comando.
USUARIO_DEMO = "demo"
SENHA_DEMO = "senha-de-demonstracao-123"

# Slug da receita usada na auditoria da página de detalhe. É o slug do título abaixo
# (o ``gerar_slug_unico`` o deriva) e o .github/lighthouse/*.json o cita: mudar o
# título exige mudar lá (o teste de configuração confere).
SLUG_RECEITA_AUDITADA = "bolo-de-cenoura-com-cobertura-de-chocolate"


class DadosReceita(TypedDict):
    """Campos de uma receita de demonstração (o autor e a capa saem do comando)."""

    titulo: str
    resumo: str
    categoria: str
    tags: list[str]
    tempo: int
    porcoes: int


RECEITAS: list[DadosReceita] = [
    {
        "titulo": "Bolo de cenoura com cobertura de chocolate",
        "resumo": "Fofinho por dentro, com uma cobertura que racha de leve ao morder.",
        "categoria": "Sobremesas",
        "tags": ["Clássicos"],
        "tempo": 55,
        "porcoes": 12,
    },
    {
        "titulo": "Macarrão ao alho e óleo",
        "resumo": "Três ingredientes e dez minutos: o jantar de quem chegou tarde.",
        "categoria": "Massas",
        "tags": ["Rápidas", "Vegetarianas"],
        "tempo": 15,
        "porcoes": 2,
    },
    {
        "titulo": "Risoto de cogumelos",
        "resumo": "Cremoso sem creme de leite: o segredo é mexer e ter paciência.",
        "categoria": "Massas",
        "tags": ["Vegetarianas"],
        "tempo": 40,
        "porcoes": 4,
    },
    {
        "titulo": "Brigadeiro de panela",
        "resumo": "O doce de festa em versão de colher, direto da panela.",
        "categoria": "Sobremesas",
        "tags": ["Rápidas", "Clássicos"],
        "tempo": 20,
        "porcoes": 8,
    },
]

COMENTARIOS = [
    "Fiz no domingo e acabou em duas horas. A cobertura é perfeita!",
    "Troquei o chocolate por cacau e também ficou ótimo.",
]


class Command(BaseCommand):
    """
    Cria categorias, tags, receitas e comentários de demonstração.

    Idempotente e restrito a ``DEBUG=True``; ver a docstring do módulo.

    Uso::

        uv run python manage.py semear_dados_demo
    """

    help = "Cria dados de demonstração (só com DEBUG=True) para auditorias e testes."

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Cria cada grupo de dados e informa o total ao final.

        Fluxo:
            1. Recusa rodar se ``DEBUG`` estiver desligado.
            2. Cria (ou reaproveita) o usuário de demonstração.
            3. Cria as receitas, com categoria, tags e capa.
            4. Cria os comentários na primeira receita.
            5. Imprime o total de receitas e comentários.

        Args:
            *args (Any): argumentos posicionais (não utilizados).
            **options (Any): argumentos nomeados do parser (não utilizados).

        Raises:
            CommandError: se ``settings.DEBUG`` for falso.
        """
        if not settings.DEBUG:
            raise CommandError(
                "semear_dados_demo só roda com DEBUG=True: são dados de "
                "demonstração, nunca de produção."
            )

        autor = self._usuario()
        receitas = self._receitas(autor)
        self._comentarios(receitas[0], autor)
        self.stdout.write(
            self.style.SUCCESS(
                f"Dados de demonstração prontos: {Receita.objects.count()} receitas, "
                f"{Comentario.objects.count()} comentários."
            )
        )

    # -------------------------------------------------------------------------
    # Utilitários
    # -------------------------------------------------------------------------
    @staticmethod
    def _imagem(nome: str, indice: int) -> ContentFile[bytes]:
        """
        Gera um gradiente JPEG para usar como capa de receita.

        Args:
            nome (str): nome do arquivo da capa.
            indice (int): posição na paleta ``CORES`` (dá a volta ao passar do fim).

        Returns:
            ContentFile[bytes]: arquivo em memória, pronto para atribuir ao campo.
        """
        topo, base = CORES[indice % len(CORES)]
        gradiente = Image.linear_gradient("L").resize((1200, 800))
        imagem = ImageOps.colorize(gradiente, black=base, white=topo)
        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=80)
        return ContentFile(buffer.getvalue(), name=nome)

    # -------------------------------------------------------------------------
    # Criação dos dados
    # -------------------------------------------------------------------------
    @staticmethod
    def _usuario() -> User:
        """
        Cria (ou reaproveita) o usuário que assina receitas e comentários.

        Returns:
            User: o usuário de demonstração.
        """
        usuario, criado = User.objects.get_or_create(username=USUARIO_DEMO)
        if criado:
            usuario.set_password(SENHA_DEMO)
            usuario.save()
        return usuario

    def _receitas(self, autor: User) -> list[Receita]:
        """
        Cria as receitas de ``RECEITAS`` com categoria, tags e capa.

        Args:
            autor (User): autor de todas as receitas.

        Returns:
            list[Receita]: as receitas, na ordem de ``RECEITAS``.
        """
        criadas: list[Receita] = []
        for indice, dados in enumerate(RECEITAS):
            categoria, _ = Categoria.objects.get_or_create(nome=dados["categoria"])
            receita, nova = Receita.objects.get_or_create(
                titulo=dados["titulo"],
                defaults={
                    "resumo": dados["resumo"],
                    # Um item por linha, sem marcador: o cartão de ingredientes já é
                    # uma lista, e o "- " aparecia escrito na frente de cada item.
                    "ingredientes": "3 ingredientes principais\n1 pitada de sal",
                    "modo_de_preparo": (
                        "1. Separe e meça tudo antes de começar.\n"
                        "2. Misture na ordem da lista.\n"
                        "3. Leve ao fogo ou ao forno até o ponto certo."
                    ),
                    "tempo_preparo_minutos": dados["tempo"],
                    "porcoes": dados["porcoes"],
                    "categoria": categoria,
                    "autor": autor,
                    "publicado": True,
                },
            )
            if nova:
                receita.imagem_capa.save(
                    f"demo-{indice}.jpg", self._imagem(f"demo-{indice}.jpg", indice)
                )
                for nome_tag in dados["tags"]:
                    tag, _ = Tag.objects.get_or_create(nome=nome_tag)
                    receita.tags.add(tag)
            criadas.append(receita)
        return criadas

    @staticmethod
    def _comentarios(receita: Receita, autor: User) -> None:
        """
        Cria os comentários de demonstração numa receita.

        Args:
            receita (Receita): receita que recebe os comentários.
            autor (User): autor dos comentários.
        """
        for texto in COMENTARIOS:
            Comentario.objects.get_or_create(
                receita=receita, autor=autor, texto=texto, defaults={"aprovado": True}
            )
