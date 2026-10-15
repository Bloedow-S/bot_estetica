"""Ponto de entrada: recebe os webhooks da Meta e responde pelo WhatsApp."""
import os

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response

from flow import tratar_mensagem
from whatsapp import enviar_texto

load_dotenv()

app = FastAPI()

# Senha combinada com a Meta no cadastro do webhook (mesmo valor do painel).
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]

# IDs das mensagens já tratadas. A Meta reenvia o mesmo evento se não receber
# resposta rápida, e sem este controle o bot responderia em duplicidade.
# O conjunto cresce devagar, o que é aceitável para o volume de uma clínica.
PROCESSADAS = set()


@app.get("/webhook")
def verificar(
    modo: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    desafio: str = Query(None, alias="hub.challenge"),
):
    # Chamada única, feita pela Meta ao cadastrar a URL. Devolver o desafio
    # prova que o endereço é nosso e que conhecemos o token combinado.
    if modo == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=desafio, media_type="text/plain")
    raise HTTPException(status_code=403)


def processar(corpo):
    """Lê o JSON da Meta, roda a lógica da conversa e envia a resposta."""
    try:
        valor = corpo["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError):
        return

    # Eventos de entrega e leitura chegam neste mesmo webhook e não trazem
    # "messages". Nesse caso o laço abaixo simplesmente não executa.
    for msg in valor.get("messages", []):
        if msg["id"] in PROCESSADAS:
            continue
        PROCESSADAS.add(msg["id"])

        telefone = msg["from"]
        if msg["type"] != "text":
            enviar_texto(telefone, "Por enquanto só consigo responder mensagens de texto.")
            continue

        resposta = tratar_mensagem(telefone, msg["text"]["body"])
        if resposta:  # None significa "ficar em silêncio" (atendimento humano)
            enviar_texto(telefone, resposta)


@app.post("/webhook")
async def receber(request: Request, tarefas: BackgroundTasks):
    corpo = await request.json()

    # O trabalho pesado roda em segundo plano para devolver o status 200 de
    # imediato. Se a Meta não receber o 200 em poucos segundos, ela assume
    # falha e reenvia a mensagem.
    tarefas.add_task(processar, corpo)
    return {"status": "ok"}
