"""
Formulário de comentário em receita (spec 005), com honeypot e time-trap
antibot (spec 007).
"""

from __future__ import annotations

import time

from django import forms
from django.core import signing
from django.http import QueryDict

from .models import Comentario

# Namespace da assinatura do carimbo de tempo -- evita que um valor assinado
# por outra parte do projeto seja aceito aqui por engano (spec 007, ADR-2).
_ASSINATURA_SALT = "receitas.comentario.antibot"

# Tempo mínimo plausível entre a página carregar e o comentário chegar; um
# envio mais rápido que isso é tratado como bot (spec 007, RF-02, ADR-4).
_TEMPO_MINIMO_SEGUNDOS = 2


def gerar_carimbo_de_tempo() -> str:
    """
    Assina o instante atual, para detectar envios rápidos demais (RF-02).

    Chamada pela view no GET que renderiza o formulário -- o carimbo viaja
    como campo hidden e volta no POST correspondente.

    Returns:
        str: o timestamp atual (``time.time()``), assinado via
        ``django.core.signing``.
    """
    return signing.dumps(time.time(), salt=_ASSINATURA_SALT)


def eh_envio_suspeito_de_bot(dados: QueryDict) -> bool:
    """
    Detecta honeypot preenchido ou time-trap disparado (spec 007).

    Lê ``request.POST`` diretamente, antes de qualquer validação do
    ``FormularioComentario`` -- um honeypot preenchido deve ser rejeitado
    mesmo que o resto do envio (``texto``) seja inválido (ADR-3).

    Args:
        dados (QueryDict): ``request.POST`` do envio do formulário de
            comentário.

    Returns:
        bool: True se ``endereco_web`` (o honeypot) veio não-vazio, ou se
        ``carimbo_tempo`` está ausente/adulterado ou indica um envio mais
        rápido que ``_TEMPO_MINIMO_SEGUNDOS`` (RF-01, RF-02).
    """
    if dados.get("endereco_web", "").strip():
        return True

    try:
        momento_renderizado = signing.loads(
            dados.get("carimbo_tempo", ""), salt=_ASSINATURA_SALT
        )
    except signing.BadSignature:
        return True

    return (time.time() - momento_renderizado) < _TEMPO_MINIMO_SEGUNDOS


class FormularioComentario(forms.ModelForm):
    """
    Comentário de uma linha só: o texto, mais dois campos antibot.

    ``receita`` e ``autor`` são preenchidos pela view a partir da URL e do
    usuário autenticado — não fazem parte do formulário. ``endereco_web``
    e ``carimbo_tempo`` também não são campos do modelo — existem só para
    ``eh_envio_suspeito_de_bot()`` (spec 007); ``form.save()`` os ignora
    automaticamente por não estarem em ``Meta.fields``.
    """

    # Honeypot (RF-01): campo de texto real, oculto só por CSS
    # (`.campo-armadilha`) -- um `HiddenInput` seria ignorado por bots já
    # preparados para reconhecer honeypots (spec 007, ADR-1).
    endereco_web = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    # Time-trap (RF-02): carimbo assinado do instante de renderização,
    # preenchido pela view via `initial` no GET.
    carimbo_tempo = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Comentario
        fields = ["texto"]
        widgets = {
            "texto": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Deixe seu comentário..."}
            ),
        }
        labels = {"texto": "Comentário"}

    def clean_texto(self) -> str:
        """
        Rejeita comentário vazio ou só com espaços em branco (RF-05).

        ``TextField`` sem ``blank=False`` já rejeita string vazia, mas uma
        string só de espaços passa pela validação padrão do Django (é
        "verdadeira") — daí o ``.strip()`` explícito aqui.

        Returns:
            str: o texto já sem espaços nas pontas.

        Raises:
            django.core.exceptions.ValidationError: se o texto, após
                ``.strip()``, ficar vazio.
        """
        texto = self.cleaned_data["texto"].strip()
        if not texto:
            raise forms.ValidationError("O comentário não pode ficar vazio.")
        return texto
