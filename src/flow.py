"""Lógica da conversa: uma máquina de estados por número de telefone."""
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

# Procedimentos (nome, valor, duração) ficam em um JSON, não no código.
# Assim a cliente altera preços e serviços sem mexer em Python.
RAIZ = Path(__file__).resolve().parent.parent
PROCEDIMENTOS = json.loads(
    (RAIZ / "data" / "procedimentos.json").read_text(encoding="utf-8")
)

# Dados pedidos ao cliente ao final do fluxo, em ordem. O telefone não
# entra aqui porque já vem na própria mensagem do WhatsApp. Por mínimo
# necessário (LGPD), só o nome é pedido; para exigir CPF e endereço,
# basta descomentar as linhas.
CAMPOS = [
    ("nome", "Qual é o seu nome completo?"),
    # ("cpf", "Informe o seu CPF:"),
    # ("endereco", "Informe o seu endereço:"),
]

# Estados possíveis da conversa.
INICIO = "inicio"
ESCOLHENDO_PROCEDIMENTO = "escolhendo_procedimento"
ESCOLHENDO_DATA = "escolhendo_data"
ESCOLHENDO_HORARIO = "escolhendo_horario"
COLETANDO_DADOS = "coletando_dados"
CONFIRMANDO = "confirmando"
HUMANO = "humano"

# Memória das conversas: telefone -> {"estado": ..., "dados": {...}}.
# Fica na memória do processo, então reiniciar o servidor zera tudo. Nesse
# caso a pessoa só recomeça pelo menu. Em desenvolvimento, o --reload do
# uvicorn reinicia a cada arquivo salvo e também zera as conversas.
conversas = {}


def horarios_disponiveis(dia, duracao_min):
    # PROVISÓRIO: lista fixa. Será substituída pela função que usa o
    # freebusy do Google Agenda (horário de funcionamento menos ocupados).
    return ["09:00", "10:30", "14:00", "15:30"]


def moeda(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


def reiniciar(conversa):
    conversa["estado"] = INICIO
    conversa["dados"] = {}


def menu_procedimentos():
    linhas = [
        f"{p['id']} - {p['nome']} ({moeda(p['valor'])}, {p['duracao_min']} min)"
        for p in PROCEDIMENTOS
    ]
    return (
        "Olá! Sou o assistente virtual da clínica. "
        "Qual procedimento você procura?\n\n"
        + "\n".join(linhas)
        + "\n\nResponda com o número do procedimento. "
        "A qualquer momento, digite MENU para recomeçar "
        "ou ATENDENTE para falar com uma pessoa."
    )


# --- Um tratador por estado -------------------------------------------------
# Cada função recebe a conversa e o texto, decide a próxima etapa e devolve
# a resposta. Separar por estado deixa o fluxo fácil de ler e de ampliar.


def tratar_inicio(conversa, texto):
    # Qualquer primeira mensagem ("oi", "bom dia"...) abre o menu.
    conversa["estado"] = ESCOLHENDO_PROCEDIMENTO
    return menu_procedimentos()


def tratar_procedimento(conversa, texto):
    escolhido = next((p for p in PROCEDIMENTOS if p["id"] == texto), None)
    if not escolhido:
        return "Não entendi. Responda com o número de um dos procedimentos da lista."

    conversa["dados"]["procedimento"] = escolhido
    conversa["estado"] = ESCOLHENDO_DATA
    return (
        f"{escolhido['nome']}: {moeda(escolhido['valor'])}, "
        f"duração de {escolhido['duracao_min']} minutos.\n\n"
        "Para qual dia você quer agendar? Informe no formato DD/MM, por exemplo 20/10."
    )


def tratar_data(conversa, texto):
    # Qualquer formato inválido (texto solto, dia 31/02...) cai no mesmo erro.
    try:
        dia_txt, mes_txt = texto.split("/")
        hoje = datetime.now(FUSO).date()
        dia = date(hoje.year, int(mes_txt), int(dia_txt))
        if dia < hoje:  # data que já passou neste ano vale para o ano seguinte
            dia = date(hoje.year + 1, int(mes_txt), int(dia_txt))
    except ValueError:
        return "Data inválida. Use o formato DD/MM, por exemplo 20/10."

    duracao = conversa["dados"]["procedimento"]["duracao_min"]
    opcoes = horarios_disponiveis(dia, duracao)
    if not opcoes:
        return "Não há horários livres nesse dia. Informe outra data (DD/MM)."

    conversa["dados"]["data"] = dia
    conversa["dados"]["opcoes_horario"] = opcoes
    conversa["estado"] = ESCOLHENDO_HORARIO
    lista = "\n".join(f"{i} - {h}" for i, h in enumerate(opcoes, start=1))
    return f"Horários disponíveis em {dia.strftime('%d/%m/%Y')}:\n\n{lista}\n\nResponda com o número do horário."


def tratar_horario(conversa, texto):
    dados = conversa["dados"]
    opcoes = dados["opcoes_horario"]
    if not texto.isdigit() or not 1 <= int(texto) <= len(opcoes):
        return "Responda com o número de um dos horários da lista."

    dados["horario"] = opcoes[int(texto) - 1]
    dados["indice_campo"] = 0
    conversa["estado"] = COLETANDO_DADOS
    return CAMPOS[0][1]


def tratar_dados(conversa, texto):
    # Guarda a resposta do campo atual e avança para o próximo. Quando os
    # campos acabam, vai para a confirmação.
    dados = conversa["dados"]
    i = dados["indice_campo"]
    dados[CAMPOS[i][0]] = texto

    if i + 1 < len(CAMPOS):
        dados["indice_campo"] = i + 1
        return CAMPOS[i + 1][1]

    conversa["estado"] = CONFIRMANDO
    p = dados["procedimento"]
    return (
        "Confira os dados:\n\n"
        f"Procedimento: {p['nome']} ({moeda(p['valor'])})\n"
        f"Data: {dados['data'].strftime('%d/%m/%Y')}\n"
        f"Horário: {dados['horario']}\n"
        f"Nome: {dados['nome']}\n\n"
        "Está correto? Responda SIM ou NÃO."
    )


def tratar_confirmacao(conversa, texto):
    resposta = texto.lower()

    if resposta in ("sim", "s"):
        # PRÓXIMO PASSO: criar o evento no Calendar e gravar na planilha aqui.
        # Enquanto isso não existe, nada foi reservado de fato, por isso a
        # mensagem fala em "solicitação" e não em "agendamento confirmado".
        dados = conversa["dados"]
        mensagem = (
            "Solicitação recebida! "
            f"{dados['procedimento']['nome']} em {dados['data'].strftime('%d/%m/%Y')} "
            f"às {dados['horario']}. A clínica confirmará em breve."
        )
        reiniciar(conversa)
        return mensagem

    if resposta in ("nao", "não", "n"):
        reiniciar(conversa)
        return "Tudo bem, cancelei a solicitação. Digite MENU para recomeçar."

    return "Responda SIM ou NÃO."


TRATADORES = {
    INICIO: tratar_inicio,
    ESCOLHENDO_PROCEDIMENTO: tratar_procedimento,
    ESCOLHENDO_DATA: tratar_data,
    ESCOLHENDO_HORARIO: tratar_horario,
    COLETANDO_DADOS: tratar_dados,
    CONFIRMANDO: tratar_confirmacao,
}


def tratar_mensagem(telefone, texto):
    """Recebe a mensagem de um telefone e devolve a resposta (ou None)."""
    texto = texto.strip()
    comando = texto.lower()

    # Cada telefone tem a própria conversa. É o `telefone` que mantém os
    # clientes separados, já que cada webhook chega isolado e sem memória.
    conversa = conversas.setdefault(telefone, {"estado": INICIO, "dados": {}})

    # Comandos que valem em qualquer etapa.
    if comando in ("menu", "cancelar", "recomeçar", "recomecar"):
        reiniciar(conversa)
        return tratar_inicio(conversa, texto)

    if comando == "atendente":
        # PRÓXIMO PASSO: avisar a diretora (notificação ainda não existe).
        conversa["estado"] = HUMANO
        return "Certo, uma pessoa da clínica falará com você em breve."

    # Durante o atendimento humano o bot fica em silêncio até o cliente
    # digitar MENU, para não atropelar a conversa.
    if conversa["estado"] == HUMANO:
        return None

    tratador = TRATADORES.get(conversa["estado"], tratar_inicio)
    return tratador(conversa, texto)
