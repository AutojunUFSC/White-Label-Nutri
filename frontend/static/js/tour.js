// Tour de boas-vindas guiado: escurece a tela, destaca o elemento do passo e mostra um
// cartão ao lado dele. Percorre várias telas: o roteiro e o passo atual ficam na aba
// (sessionStorage), então o passeio continua depois de cada clique.
//
// Entrada: o JSON #tour-dados (só no primeiro acesso e na Ajuda) e o atributo
// data-rota do <body>. Passos "clicar" deixam só o elemento destacado clicável;
// passos "proximo" têm um botão. Se a pessoa sair do roteiro, o tour se encerra.
(function () {
  "use strict";

  const CHAVE = "tour:estado";
  const VALIDADE_MS = 30 * 60 * 1000; // um passeio abandonado não reaparece depois disso
  const FOLGA = 12; // px entre o cartão e a borda da tela / do destaque
  const MARGEM_DESTAQUE = 6; // px ao redor do elemento destacado

  const armazenamento = {
    ler: function () {
      try {
        const bruto = window.sessionStorage.getItem(CHAVE);
        return bruto ? JSON.parse(bruto) : null;
      } catch (erro) {
        return null;
      }
    },
    gravar: function (estado) {
      try {
        window.sessionStorage.setItem(CHAVE, JSON.stringify(estado));
      } catch (erro) {
        /* sem armazenamento (aba privada): o tour só roda nesta tela */
      }
    },
    limpar: function () {
      try {
        window.sessionStorage.removeItem(CHAVE);
      } catch (erro) {
        /* nada a limpar */
      }
    },
  };

  const elementoDados = document.getElementById("tour-dados");
  const dados = elementoDados ? JSON.parse(elementoDados.textContent) : null;
  const rota = document.body.dataset.rota;

  // Sair do sistema encerra o passeio: outra pessoa pode entrar na mesma aba.
  document.querySelectorAll('a[href$="logoutUser"]').forEach(function (link) {
    link.addEventListener("click", armazenamento.limpar);
  });

  // Botão "Ver o tour de novo" (Ajuda): recomeça pela lista de fichas.
  document.querySelectorAll("[data-tour-abrir]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      if (!dados) {
        return;
      }
      armazenamento.gravar({ passos: dados.passos, i: 0, em: Date.now() });
      window.location.href = dados.inicio;
    });
  });

  let estado = armazenamento.ler();
  if (estado && Date.now() - estado.em > VALIDADE_MS) {
    armazenamento.limpar();
    estado = null;
  }
  if (dados && dados.automatico) {
    estado = { passos: dados.passos, i: 0, em: Date.now() };
    armazenamento.gravar(estado);
  }
  if (!estado) {
    return;
  }

  const reduzMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let camada = null; // elementos do tour, criados na primeira exibição
  let paineis = [];
  let anel = null;
  let bloqueio = null;
  let cartao = null;
  let alvoAtual = null;
  let aoClicarAlvo = null;
  let quadro = 0;

  function criar(tag, classe) {
    const el = document.createElement(tag);
    el.className = classe;
    return el;
  }

  function construir() {
    camada = criar("div", "tour-camada");
    paineis = [0, 1, 2, 3].map(function () {
      const painel = criar("div", "tour-painel");
      camada.appendChild(painel);
      return painel;
    });
    anel = criar("div", "tour-anel");
    bloqueio = criar("div", "tour-bloqueio");
    cartao = criar("div", "tour-cartao");
    cartao.setAttribute("role", "dialog");
    cartao.setAttribute("aria-labelledby", "tour-titulo");
    cartao.setAttribute("aria-describedby", "tour-texto");
    cartao.setAttribute("aria-live", "polite");
    cartao.tabIndex = -1;
    camada.appendChild(anel);
    camada.appendChild(bloqueio);
    camada.appendChild(cartao);
    document.body.appendChild(camada);
    window.addEventListener("resize", agendar);
    window.addEventListener("scroll", agendar, true);
    window.addEventListener("load", agendar);
    document.addEventListener("keydown", aoTeclar);
  }

  function aoTeclar(evento) {
    if (evento.key === "Escape") {
      encerrar();
    }
  }

  function encerrar() {
    armazenamento.limpar();
    desligarAlvo();
    window.removeEventListener("resize", agendar);
    window.removeEventListener("scroll", agendar, true);
    window.removeEventListener("load", agendar);
    document.removeEventListener("keydown", aoTeclar);
    if (camada) {
      camada.remove();
      camada = null;
    }
  }

  function desligarAlvo() {
    if (alvoAtual && aoClicarAlvo) {
      alvoAtual.removeEventListener("click", aoClicarAlvo);
    }
    alvoAtual = null;
    aoClicarAlvo = null;
  }

  function avancar() {
    estado.i += 1;
    estado.em = Date.now();
    armazenamento.gravar(estado);
    exibir();
  }

  // No celular o menu fica recolhido: abre-o para o destaque ter onde cair.
  function tornarVisivel(alvo, pronto) {
    if (alvo.getClientRects().length > 0) {
      pronto();
      return;
    }
    const recolhido = alvo.closest(".collapse");
    if (recolhido && window.bootstrap) {
      recolhido.addEventListener("shown.bs.collapse", pronto, { once: true });
      window.bootstrap.Collapse.getOrCreateInstance(recolhido, { toggle: false }).show();
    } else {
      pronto();
    }
  }

  function exibir() {
    desligarAlvo();
    const passo = estado.passos[estado.i];
    if (!passo || passo.rota !== rota) {
      encerrar(); // fim do roteiro, ou a pessoa saiu dele
      return;
    }
    const alvo = passo.alvo ? document.querySelector(passo.alvo) : null;
    if (passo.alvo && !alvo) {
      avancar(); // o elemento não existe nesta tela: pula o passo
      return;
    }
    if (!camada) {
      construir();
    }
    if (!alvo) {
      mostrar(passo, null);
      return;
    }
    tornarVisivel(alvo, function () {
      const caixa = alvo.getBoundingClientRect();
      if (caixa.top < 0 || caixa.bottom > window.innerHeight) {
        alvo.scrollIntoView({ block: "center" });
      }
      mostrar(passo, alvo);
    });
  }

  function mostrar(passo, alvo) {
    alvoAtual = alvo;
    const clicar = passo.acao === "clicar";
    cartao.textContent = "";

    const contagem = criar("p", "tour-contagem");
    contagem.textContent = "Passo " + (estado.i + 1) + " de " + estado.passos.length;
    const titulo = criar("h2", "tour-titulo");
    titulo.id = "tour-titulo";
    titulo.textContent = passo.titulo;
    const texto = criar("p", "tour-texto");
    texto.id = "tour-texto";
    texto.textContent = passo.texto;
    cartao.append(contagem, titulo, texto);

    if (clicar) {
      const dica = criar("p", "tour-dica");
      dica.textContent = "Clique no item destacado para continuar.";
      cartao.appendChild(dica);
    }

    const rodape = criar("div", "tour-rodape");
    const sair = criar("button", "btn btn-link");
    sair.type = "button";
    sair.textContent = "Sair do tour";
    sair.addEventListener("click", encerrar);
    rodape.appendChild(sair);
    let proximo = null;
    if (!clicar) {
      proximo = criar("button", "btn btn-primario-instancia");
      proximo.type = "button";
      proximo.textContent = passo.botao || "Próximo";
      proximo.addEventListener("click", avancar);
      rodape.appendChild(proximo);
    }
    cartao.appendChild(rodape);

    if (alvo && clicar) {
      // Só grava o avanço; a tela seguinte retoma o roteiro depois da navegação.
      aoClicarAlvo = function () {
        estado.i += 1;
        estado.em = Date.now();
        armazenamento.gravar(estado);
      };
      alvo.addEventListener("click", aoClicarAlvo);
    }

    bloqueio.hidden = !alvo || clicar; // passos "proximo" impedem o clique no destaque
    anel.hidden = !alvo;
    posicionar();

    if (clicar && alvo) {
      alvo.focus({ preventScroll: true });
    } else if (proximo) {
      proximo.focus({ preventScroll: true });
    }
  }

  function agendar() {
    if (!quadro) {
      quadro = window.requestAnimationFrame(function () {
        quadro = 0;
        posicionar();
      });
    }
  }

  function definir(el, esquerda, topo, largura, altura) {
    el.style.left = esquerda + "px";
    el.style.top = topo + "px";
    el.style.width = Math.max(0, largura) + "px";
    el.style.height = Math.max(0, altura) + "px";
  }

  function limitar(valor, minimo, maximo) {
    return Math.max(minimo, Math.min(valor, maximo));
  }

  function posicionar() {
    if (!camada) {
      return;
    }
    const largura = window.innerWidth;
    const altura = window.innerHeight;

    if (!alvoAtual) {
      // Cartão centralizado: a tela inteira escurece.
      definir(paineis[0], 0, 0, largura, altura);
      for (let i = 1; i < paineis.length; i += 1) {
        definir(paineis[i], 0, 0, 0, 0);
      }
      cartao.classList.add("tour-cartao--centro");
      cartao.style.top = "";
      cartao.style.left = "";
      cartao.style.width = Math.min(380, largura - 2 * FOLGA) + "px";
      return;
    }

    cartao.classList.remove("tour-cartao--centro");
    const caixa = alvoAtual.getBoundingClientRect();
    const x = Math.max(caixa.left - MARGEM_DESTAQUE, 0);
    const y = Math.max(caixa.top - MARGEM_DESTAQUE, 0);
    const x2 = Math.min(caixa.right + MARGEM_DESTAQUE, largura);
    const y2 = Math.min(caixa.bottom + MARGEM_DESTAQUE, altura);

    // Quatro painéis em volta do destaque: escurecem e bloqueiam o resto da tela.
    definir(paineis[0], 0, 0, largura, y);
    definir(paineis[1], 0, y2, largura, altura - y2);
    definir(paineis[2], 0, y, x, y2 - y);
    definir(paineis[3], x2, y, largura - x2, y2 - y);
    definir(anel, x, y, x2 - x, y2 - y);
    definir(bloqueio, x, y, x2 - x, y2 - y);

    const larguraCartao = Math.min(340, largura - 2 * FOLGA);
    cartao.style.width = larguraCartao + "px";
    const alturaCartao = cartao.offsetHeight;
    let esquerda;
    let topo;
    if (largura < 576) {
      // Celular: o cartão ocupa a faixa da tela oposta ao destaque.
      esquerda = FOLGA;
      topo = (y + y2) / 2 > altura / 2 ? FOLGA : altura - alturaCartao - FOLGA;
    } else if (alvoAtual.closest(".app-lateral") && x2 + FOLGA + larguraCartao <= largura - FOLGA) {
      // Menu lateral: o cartão aparece ao lado, sem cobrir os outros itens.
      esquerda = x2 + FOLGA;
      topo = limitar(y, FOLGA, altura - alturaCartao - FOLGA);
    } else {
      esquerda = limitar(x, FOLGA, largura - larguraCartao - FOLGA);
      if (y2 + FOLGA + alturaCartao <= altura - FOLGA) {
        topo = y2 + FOLGA;
      } else if (y - FOLGA - alturaCartao >= FOLGA) {
        topo = y - FOLGA - alturaCartao;
      } else {
        topo = Math.max(FOLGA, altura - alturaCartao - FOLGA);
      }
    }
    cartao.style.left = esquerda + "px";
    cartao.style.top = topo + "px";
  }

  exibir();
})();
