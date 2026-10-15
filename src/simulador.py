"""Conversa local com o bot pelo terminal, sem WhatsApp, Meta ou internet.
 
Serve para desenvolver e testar o fluxo (flow.py) sem nenhuma credencial.
 
Uso, da raiz do projeto e com o venv ativo:
    python src/simulador.py
"""
from flow import tratar_mensagem
 
# Número fictício: o fluxo usa o telefone só para separar as conversas.
TELEFONE_FAKE = "5500000000000"
 
print("Simulador do bot. Digite como se fosse o cliente. Ctrl+C para sair.\n")
 
while True:
    try:
        texto = input("Cliente: ")
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")
        break
 
    resposta = tratar_mensagem(TELEFONE_FAKE, texto)
    print(f"Bot: {resposta}\n" if resposta else "Bot: (em silêncio)\n")
 