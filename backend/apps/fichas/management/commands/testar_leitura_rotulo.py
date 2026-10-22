"""Roda a leitura por foto numa pasta de fotos e grava um CSV para conferência.

    python backend/manage.py testar_leitura_rotulo caminho/das/fotos --saida leitura.csv

Cada linha é uma foto; as colunas são os campos lidos. Abra no Excel ao lado dos
rótulos e marque os erros — é assim que se mede a taxa de acerto antes de liberar.
Cada foto é uma chamada paga (ou da cota gratuita) ao Gemini.
"""
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.fichas import leitura_rotulo
from apps.fichas.dominio.nutrientes import NUTRIENTES

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}
COLUNAS_FIXAS = ["foto", "erro", "nomeIng", "origemDosDados", "qtdeDoIngrediente"]


class Command(BaseCommand):
    help = "Lê as fotos de tabelas nutricionais de uma pasta e grava os resultados em CSV."

    def add_arguments(self, parser):
        parser.add_argument("pasta")
        parser.add_argument("--saida", default="leitura_rotulos.csv")

    def handle(self, *args, pasta, saida, **opcoes):
        if not leitura_rotulo.leitura_habilitada():
            raise CommandError("Defina GEMINI_API_KEY no .env.")
        fotos = sorted(p for p in Path(pasta).iterdir() if p.suffix.lower() in EXTENSOES)
        if not fotos:
            raise CommandError(f"Nenhuma foto em {pasta}.")

        colunas = COLUNAS_FIXAS + [n.chave for n in NUTRIENTES] + ["conferir", "avisos"]
        with open(saida, "w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=colunas, delimiter=";",
                                      extrasaction="ignore")
            escritor.writeheader()
            for foto in fotos:
                linha = {"foto": foto.name}
                try:
                    resultado = leitura_rotulo.ler_rotulo(foto.read_bytes())
                    linha.update(resultado["campos"])
                    linha["conferir"] = ", ".join(resultado["conferir"])
                    linha["avisos"] = " | ".join(resultado["avisos"])
                    self.stdout.write(f"ok    {foto.name}")
                except leitura_rotulo.FalhaNaLeitura as erro:
                    linha["erro"] = str(erro)
                    self.stdout.write(self.style.WARNING(f"falha {foto.name}: {erro}"))
                escritor.writerow(linha)
        self.stdout.write(self.style.SUCCESS(f"{len(fotos)} fotos → {saida}"))
