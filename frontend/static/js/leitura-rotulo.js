// Pré-preenche o cadastro de ingrediente a partir da foto da tabela nutricional.
// O servidor (views.ler_rotulo_ingrediente) devolve {campos, conferir, avisos};
// nada é salvo até a pessoa revisar e clicar em "Salvar ingrediente".
(function () {
  "use strict";

  const caixa = document.querySelector("[data-leitura-rotulo]");
  if (!caixa) return;
  const entrada = caixa.querySelector("#fotoRotulo");
  const botao = caixa.querySelector("label[for=fotoRotulo]");
  const status = caixa.querySelector("[data-leitura-status]");
  const listaAvisos = caixa.querySelector("[data-leitura-avisos]");
  const csrf = document.querySelector("input[name=csrfmiddlewaretoken]").value;

  // Texto de identificação só é preenchido se a pessoa ainda não digitou nada.
  const SO_SE_VAZIO = ["nomeIng", "origemDosDados", "composicao"];

  function mostrarStatus(texto, erro) {
    status.textContent = texto;
    status.classList.toggle("text-danger", Boolean(erro));
    status.classList.toggle("text-secondary", !erro);
  }

  function limparDestaques() {
    document.querySelectorAll(".campo-lido").forEach(function (el) {
      el.classList.remove("campo-lido", "is-invalid");
    });
    listaAvisos.replaceChildren();
  }

  function preencher(resultado) {
    limparDestaques();
    let preenchidos = 0;
    Object.keys(resultado.campos).forEach(function (chave) {
      const campo = document.getElementById("id_" + chave);
      if (!campo) return;
      if (SO_SE_VAZIO.includes(chave) && campo.value.trim()) return;
      campo.value = resultado.campos[chave];
      campo.classList.add("campo-lido");
      if (resultado.conferir.includes(chave)) campo.classList.add("is-invalid");
      preenchidos += 1;
    });
    resultado.avisos.forEach(function (aviso) {
      const li = document.createElement("li");
      li.textContent = aviso;
      listaAvisos.appendChild(li);
    });
    mostrarStatus(preenchidos + " campos preenchidos. Confira antes de salvar.", false);
  }

  entrada.addEventListener("change", function () {
    const arquivo = entrada.files[0];
    if (!arquivo) return;
    const dados = new FormData();
    dados.append("foto", arquivo);
    botao.classList.add("disabled");
    entrada.disabled = true;
    mostrarStatus("Lendo a tabela… pode levar alguns segundos.", false);

    fetch(caixa.dataset.url, {
      method: "POST",
      body: dados,
      headers: { "X-CSRFToken": csrf },
      credentials: "same-origin",
    })
      .then(function (resposta) {
        return resposta.json().catch(function () { return {}; }).then(function (corpo) {
          if (!resposta.ok) throw new Error(corpo.erro || "Não foi possível ler a foto.");
          return corpo;
        });
      })
      .then(preencher)
      .catch(function (erro) {
        mostrarStatus(erro.message || "Não foi possível ler a foto.", true);
      })
      .finally(function () {
        botao.classList.remove("disabled");
        entrada.disabled = false;
        entrada.value = ""; // permite reenviar a mesma foto
      });
  });

  // Quando a pessoa corrige um campo lido, o destaque sai.
  document.addEventListener("input", function (e) {
    if (e.target.classList && e.target.classList.contains("campo-lido")) {
      e.target.classList.remove("campo-lido", "is-invalid");
    }
  });
})();
