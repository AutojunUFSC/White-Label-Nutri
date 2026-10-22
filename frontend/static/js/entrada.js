// Animação do painel das telas de entrada (_vitrine_entrada.html). Só apresentação:
// os números do rótulo de exemplo contam até o valor e os cartões inclinam
// acompanhando o mouse. Sem script, o painel aparece parado com os valores finais.
(function () {
  "use strict";

  const vitrine = document.querySelector("[data-vitrine]");
  if (!vitrine) return;
  const calmo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function formatar(valor, casas) {
    return valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  }

  // Contagem dos números
  if (!calmo) {
    const numeros = vitrine.querySelectorAll("[data-alvo]");
    const inicio = performance.now();
    const duracao = 1200;
    function contar(agora) {
      const p = Math.min(1, (agora - inicio) / duracao);
      const suave = 1 - Math.pow(1 - p, 3);
      numeros.forEach(function (n) {
        n.textContent = formatar(parseFloat(n.dataset.alvo) * suave, Number(n.dataset.casas || 0));
      });
      if (p < 1) requestAnimationFrame(contar);
    }
    requestAnimationFrame(contar);
  }
  // As barras de %VD crescem por transição CSS a partir desta classe
  requestAnimationFrame(function () { vitrine.classList.add("is-pronta"); });

  // Inclinação acompanhando o mouse (só com mouse de verdade)
  if (calmo || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
  let alvoX = 0, alvoY = 0, x = 0, y = 0, rodando = false;

  function animar() {
    x += (alvoX - x) * 0.08;
    y += (alvoY - y) * 0.08;
    vitrine.style.setProperty("--mx", x.toFixed(4));
    vitrine.style.setProperty("--my", y.toFixed(4));
    if (Math.abs(alvoX - x) > 0.001 || Math.abs(alvoY - y) > 0.001) {
      requestAnimationFrame(animar);
    } else {
      rodando = false;
    }
  }
  function mover(px, py) {
    alvoX = px; alvoY = py;
    if (!rodando) { rodando = true; requestAnimationFrame(animar); }
  }

  document.addEventListener("pointermove", function (e) {
    const r = vitrine.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * 2 - 1;
    const py = ((e.clientY - r.top) / r.height) * 2 - 1;
    mover(Math.max(-1, Math.min(1, px)), Math.max(-1, Math.min(1, py)));
  });
  // O mouse saiu da janela: os cartões voltam ao lugar
  document.addEventListener("mouseout", function (e) {
    if (!e.relatedTarget) mover(0, 0);
  });
})();
