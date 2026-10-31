// Tour de boas-vindas: navegação entre os passos da janela #tourModal.
// Abre sozinho quando a janela traz data-tour-automatico="true" (primeiro acesso) e
// por qualquer elemento com data-tour-abrir (botão da página Ajuda).
(function () {
  "use strict";

  const janela = document.getElementById("tourModal");
  if (!janela || !window.bootstrap) {
    return;
  }

  const passos = Array.from(janela.querySelectorAll("[data-tour-passo]"));
  const contagem = janela.querySelector("[data-tour-contagem]");
  const pontos = janela.querySelector("[data-tour-pontos]");
  const anterior = janela.querySelector("[data-tour-anterior]");
  const proximo = janela.querySelector("[data-tour-proximo]");
  const pular = janela.querySelector("[data-tour-pular]");
  const modal = window.bootstrap.Modal.getOrCreateInstance(janela);
  let atual = 0;

  passos.forEach(function () {
    pontos.appendChild(document.createElement("li"));
  });

  function mostrar(indice) {
    atual = Math.max(0, Math.min(indice, passos.length - 1));
    const ultimo = atual === passos.length - 1;
    passos.forEach(function (passo, i) {
      passo.hidden = i !== atual;
    });
    Array.from(pontos.children).forEach(function (ponto, i) {
      ponto.classList.toggle("is-ativo", i === atual);
    });
    contagem.textContent = atual + 1 + " de " + passos.length;
    anterior.disabled = atual === 0;
    pular.hidden = ultimo;
    proximo.textContent = ultimo ? "Concluir" : "Próximo";
  }

  proximo.addEventListener("click", function () {
    if (atual === passos.length - 1) {
      modal.hide();
    } else {
      mostrar(atual + 1);
    }
  });
  anterior.addEventListener("click", function () {
    mostrar(atual - 1);
  });
  pular.addEventListener("click", function () {
    modal.hide();
  });

  janela.addEventListener("keydown", function (evento) {
    if (evento.key === "ArrowRight" && atual < passos.length - 1) {
      mostrar(atual + 1);
    } else if (evento.key === "ArrowLeft" && atual > 0) {
      mostrar(atual - 1);
    }
  });

  // Sempre recomeça do primeiro passo, seja qual for a forma de fechar.
  janela.addEventListener("hidden.bs.modal", function () {
    mostrar(0);
  });

  document.querySelectorAll("[data-tour-abrir]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      mostrar(0);
      modal.show();
    });
  });

  mostrar(0);
  if (janela.dataset.tourAutomatico === "true") {
    modal.show();
  }
})();
