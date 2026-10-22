"""Formulários das telas de ficha, receita, ingrediente e membro."""
import datetime

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models.functions import Lower

from apps.fichas.models import (
    Chave,
    Ficha,
    Ficha_Ingrediente,
    Ingrediente,
    Membro,
    Nutriente,
    Tabela,
)


def aplicar_classes_bootstrap(form):
    """Adiciona as classes do Bootstrap 5 aos widgets sem repetir em cada campo."""
    for campo in form.fields.values():
        widget = campo.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(widget, forms.Select):
            widget.attrs.setdefault("class", "form-select")
        else:
            widget.attrs.setdefault("class", "form-control")


def campo_data(rotulo):
    """Data com calendário do navegador (<input type="date">), hoje como padrão.
    O navegador envia AAAA-MM-DD; DD/MM/AAAA continua aceito para quem digita."""
    return forms.DateField(
        label=rotulo,
        initial=datetime.date.today,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
    )


class LoginForm(forms.Form):
    username = forms.CharField(label="Nome", required=True)
    password = forms.CharField(label="Senha", required=True, widget=forms.PasswordInput)


class FichaFiltroForm(forms.Form):
    f_nomeFicha = forms.CharField(label="Receita", required=False)
    f_cliente = forms.CharField(label="Cliente", required=False)
    f_autor = forms.CharField(label="Autor", required=False)


class FichaFormBase(forms.ModelForm):
    dataCriacao = campo_data("Data de criação")

    class Meta:
        model = Ficha
        fields = [
            "autor", "nomeFicha", "cliente", "pesoTotal", "pesoPorcao",
            "pesoAnvisa", "dataCriacao", "medCaseiraPorcao",
        ]
        labels = {
            "autor": "Autor",
            "nomeFicha": "Nome da receita",
            "cliente": "Cliente",
            "pesoTotal": "Peso total (g)",
            "pesoPorcao": "Peso da porção — Cliente (g)",
            "pesoAnvisa": "Peso da porção — Anvisa (g)",
            "medCaseiraPorcao": "Medida caseira da porção",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["autor"].queryset = Membro.objects.all().order_by(Lower("nome"))
        aplicar_classes_bootstrap(self)


class ReceitaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classes_bootstrap(self)

    class Meta:
        model = Ficha_Ingrediente
        fields = ["pesoBruto", "pesoLiquido", "medidaCaseira", "nomeFantasia"]
        labels = {
            "pesoBruto": "Peso bruto (g)",
            "pesoLiquido": "Peso líquido (g)",
            "medidaCaseira": "Medida caseira",
            "nomeFantasia": "Nome fantasia",
        }


class NutrienteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classes_bootstrap(self)

    class Meta:
        model = Nutriente
        fields = ["nomeNutri", "qtde", "qtde_Arred", "medida", "qtde_VD"]
        labels = {
            "nomeNutri": "Novo item",
            "qtde": "Quantidade real",
            "qtde_Arred": "Quantidade arredondada",
            "medida": "Medida",
            "qtde_VD": "Quantidade valor diário",
        }


class FormInformacoesComplementares(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classes_bootstrap(self)

    class Meta:
        model = Tabela
        fields = ["informacoesComplementares"]
        labels = {"informacoesComplementares": "Informações complementares"}
        widgets = {"informacoesComplementares": forms.Textarea(attrs={"rows": 3})}


class IngredienteForm(forms.ModelForm):
    dataCriacao = campo_data("Data de criação")
    composicao = forms.CharField(
        label="Composição",
        help_text="Formato: leite, açúcar e lactose",
        required=False,
    )

    class Meta:
        model = Ingrediente
        fields = [
            "autorIng", "nomeIng", "composicao", "origemDosDados", "qtdeDoIngrediente",
            "dataCriacao", "numRef",
            "proteinas", "gordTotais", "acucaresTotais", "carboidratos", "fibras",
            "energiakcal", "energiaKJ", "calcio", "ferro", "magnesio", "fosforo",
            "potassio", "sodio", "zinco", "cobre", "manganes",
            "retinol", "RE", "vitaminaARAE", "vitaminaC", "tiamina",
            "riboflavina", "niancina", "piridoxina", "gordSat", "gordTrans",
            "gordPoli", "gordMono", "colesterol", "acucaresadd", "omega6", "omega3",
            "vitaminaD", "vitaminaE", "vitaminaK", "biotina", "acidoFolico",
            "acidoPantotenico", "vitaminaB12", "cloreto", "cromo", "fluor", "iodo",
            "molibdenio", "selenio", "colina",
        ]
        labels = {
            "autorIng": "Autor",
            "nomeIng": "Ingrediente",
            "origemDosDados": "Fonte / Marca",
            "qtdeDoIngrediente": "Quantidade do ingrediente (g)",
            "numRef": "Nº de referência",
        }
        help_texts = {
            "numRef": "Número do alimento na tabela de origem (ex.: TACO). Deixe 0 se não houver.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["autorIng"].queryset = Membro.objects.all().order_by(Lower("nome"))
        aplicar_classes_bootstrap(self)


class IngredienteFiltroForm(forms.Form):
    f_nomeIng = forms.CharField(label="Nome", required=False)
    f_origemDosDados = forms.CharField(label="Origem", required=False)
    f_autorIng = forms.CharField(label="Autor", required=False)


class UploadForm(forms.Form):
    files = forms.FileField(label="Arquivo TXT (separado por TAB)")


class MembroForm(forms.ModelForm):
    """Auto-cadastro de membro protegido pela chave da instância (BR-024)."""

    chave = forms.CharField(label="Chave de cadastro", required=True, widget=forms.PasswordInput)
    senha1 = forms.CharField(label="Senha", required=True, widget=forms.PasswordInput)
    senha2 = forms.CharField(label="Confirmar senha", required=True, widget=forms.PasswordInput)

    class Meta:
        model = Membro
        fields = ["nome", "semestre", "email"]
        labels = {
            "nome": "Nome de usuário",
            "semestre": "Semestre de entrada",
            "email": "E-mail",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classes_bootstrap(self)

    def clean(self):
        dados = super().clean()
        if dados.get("nome") and User.objects.filter(username=dados["nome"]).exists():
            self.add_error(
                "nome",
                "Já existe um usuário com esse nome. Não foi possível realizar o cadastro.",
            )
        if dados.get("senha1") and dados.get("senha2") and dados["senha1"] != dados["senha2"]:
            self.add_error(
                "senha2", "As senhas não conferem. Não foi possível realizar o cadastro."
            )
        elif dados.get("senha1"):
            # Força mínima de senha: usa os validadores do Django (AUTH_PASSWORD_VALIDATORS).
            try:
                validate_password(dados["senha1"])
            except forms.ValidationError as erro:
                self.add_error("senha1", erro)
        chave_atual = Chave.objects.last()
        if not chave_atual or dados.get("chave") != chave_atual.key:
            self.add_error("chave", "Chave incorreta. Não foi possível realizar o cadastro.")
        return dados


class ChaveForm(forms.ModelForm):
    class Meta:
        model = Chave
        fields = ["key"]
        labels = {"key": "Nova chave"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classes_bootstrap(self)


class MudarSenhaForm(forms.Form):
    """Troca de senha de qualquer membro (administradores da instância)."""

    usuario = forms.ModelChoiceField(label="Membro", required=True, queryset=User.objects.none())
    nova_senha = forms.CharField(label="Nova senha", required=True, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = User.objects.all().order_by(Lower("username"))
        aplicar_classes_bootstrap(self)

    def clean_nova_senha(self):
        senha = self.cleaned_data["nova_senha"]
        validate_password(senha)
        return senha


class ApagarMembroForm(forms.Form):
    """Exclusão de membro com transferência de autoria (BR-026)."""

    membroExcluido = forms.ModelChoiceField(
        label="Excluir membro", required=True, queryset=Membro.objects.none()
    )
    membroDestino = forms.ModelChoiceField(
        label="Transferir autoria para",
        required=True,
        queryset=Membro.objects.none(),
        help_text="Inclui as fichas e os ingredientes criados por ele",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        membros = Membro.objects.all().order_by(Lower("nome"))
        self.fields["membroExcluido"].queryset = membros
        self.fields["membroDestino"].queryset = membros
        aplicar_classes_bootstrap(self)

    def clean(self):
        dados = super().clean()
        if dados.get("membroExcluido") and dados.get("membroExcluido") == dados.get(
            "membroDestino"
        ):
            self.add_error("membroDestino", "Os dois membros precisam ser distintos")
        return dados
