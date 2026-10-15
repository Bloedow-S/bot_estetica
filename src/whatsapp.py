"""Envio de mensagens pelo WhatsApp (Graph API da Meta)."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Credenciais do número que o bot usa. Em produção, só estes valores mudam.
WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]

# Versão da Graph API. Use a que aparece no exemplo de curl do painel da Meta.
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v21.0")
URL = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"


def normalizar_telefone(numero):
    # O webhook entrega celulares brasileiros sem o nono dígito
    # (55 + DDD + 8 dígitos), mas a lista de destinatários do ambiente de
    # teste guarda o número com o 9. Sem esta correção, o envio falha com o
    # erro 131030 (destinatário fora da lista). Celulares de 8 dígitos
    # começam em 6 a 9; fixos começam em 2 a 5 e não recebem o 9.
    if numero.startswith("55") and len(numero) == 12 and numero[4] in "6789":
        return numero[:4] + "9" + numero[4:]
    return numero


def enviar_texto(para, texto):
    """Envia uma mensagem de texto para o número `para` (com DDI, só dígitos)."""
    resposta = requests.post(
        URL,
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": normalizar_telefone(para),
            "type": "text",
            "text": {"body": texto},
        },
        timeout=10,
    )

    # A Graph API responde com erro (token expirado, destinatário não
    # cadastrado...) sem derrubar o programa. Sem este log, a falha passaria
    # em silêncio e o bot pareceria simplesmente "mudo".
    if not resposta.ok:
        print(f"[ERRO ENVIO] {resposta.status_code}: {resposta.text}")
