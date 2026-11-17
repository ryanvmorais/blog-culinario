// -----------------------------------------------------------------------------
// interacoes.js
// Interações de UI globais do site (sem framework, sem build). Carregado com
// `defer` em templates/base.html, depois do DOM inteiro estar disponível.
// -----------------------------------------------------------------------------

// Largura em que o menu deixa de ser painel e volta a ser a barra do desktop;
// a mesma do @media (max-width: 720px) de static/css/base.css, seção 10.
const CONSULTA_CELULAR = "(max-width: 720px)";

// -----------------------------------------------------------------------------
// MENU MOBILE
// Alterna a classe .navbar__painel--aberto (ver static/css/base.css, seção 10),
// o véu e o inert da página, e mantém aria-expanded e aria-label sincronizados
// para leitor de tela; o CSS troca o ícone pelo aria-expanded (spec 012, ADR-7).
// Teclado (spec 008, RF-06; spec 012, RF-17): abrir leva o foco ao primeiro
// link, Esc e o X fecham e devolvem o foco ao botão, e o véu, um link do painel
// ou um clique fora da barra fecham sem mexer no foco.
// -----------------------------------------------------------------------------
const inicializarMenuMobile = () => {
  const botao = document.querySelector(".navbar__alternador");
  const painel = document.querySelector(".navbar__painel");
  const veu = document.querySelector(".navbar__veu");
  const barra = document.querySelector(".navbar");

  if (!botao || !painel || !veu || !barra) {
    return;
  }

  // A página atrás do véu sai do Tab e do leitor de tela; a barra, com o X,
  // continua alcançável, por isso o menu não é um diálogo modal (ADR-6).
  const fundo = () =>
    document.querySelectorAll("body > main, body > .mensagens, body > .rodape");

  const estaAberto = () => painel.classList.contains("navbar__painel--aberto");

  const abrirMenu = () => {
    painel.classList.add("navbar__painel--aberto");
    veu.hidden = false;
    fundo().forEach((elemento) => {
      elemento.inert = true;
    });
    document.documentElement.classList.add("menu-aberto");
    botao.setAttribute("aria-expanded", "true");
    botao.setAttribute("aria-label", "Fechar menu de navegação");
    const primeiroLink = painel.querySelector("a");
    if (primeiroLink) {
      primeiroLink.focus();
    }
  };

  // devolverFoco: com Esc e o X o foco volta ao botão; com o véu, um link ou
  // um clique fora, o visitante já escolheu outro lugar e o foco fica lá.
  const fecharMenu = ({ devolverFoco }) => {
    painel.classList.remove("navbar__painel--aberto");
    veu.hidden = true;
    fundo().forEach((elemento) => {
      elemento.inert = false;
    });
    document.documentElement.classList.remove("menu-aberto");
    botao.setAttribute("aria-expanded", "false");
    botao.setAttribute("aria-label", "Abrir menu de navegação");
    if (devolverFoco) {
      botao.focus();
    }
  };

  botao.addEventListener("click", () => {
    if (estaAberto()) {
      fecharMenu({ devolverFoco: true });
    } else {
      abrirMenu();
    }
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && estaAberto()) {
      fecharMenu({ devolverFoco: true });
    }
  });

  veu.addEventListener("click", () => {
    fecharMenu({ devolverFoco: false });
  });

  painel.addEventListener("click", (evento) => {
    if (estaAberto() && evento.target.closest("a")) {
      fecharMenu({ devolverFoco: false });
    }
  });

  document.addEventListener("click", (evento) => {
    if (estaAberto() && !barra.contains(evento.target)) {
      fecharMenu({ devolverFoco: false });
    }
  });

  // Girar o celular ou alargar a janela com o menu aberto: sem isto, o inert
  // ficaria preso na página do desktop, onde o painel não existe.
  window.matchMedia(CONSULTA_CELULAR).addEventListener("change", (consulta) => {
    if (!consulta.matches && estaAberto()) {
      fecharMenu({ devolverFoco: false });
    }
  });
};


// -----------------------------------------------------------------------------
// PONTO DE ENTRADA ÚNICO
// -----------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  inicializarMenuMobile();
});
