# Bot de agendamento via WhatsApp para clínica de estética

Projeto acadêmico. Chatbot de WhatsApp que informa os procedimentos de uma clínica de estética, com valores e horários, e registra solicitações de agendamento, consultando a disponibilidade no Google Agenda da diretora. Usa a WhatsApp Cloud API (Meta) e a Google Calendar API.

O produto será entregue à cliente sem manutenção posterior. Isso orienta as decisões de projeto: poucas dependências, contas e credenciais sob propriedade da cliente e nenhum servidor de banco de dados para administrar.

## Status atual

Concluído:

- Consulta de horários ocupados no Google Agenda (`freebusy`) por service account.
- Webhook em FastAPI: rota `GET` de verificação e rota `POST` de recebimento. A Meta já entrega as mensagens ao servidor, exposto por ngrok.
- Fluxo de conversa por número de telefone (menu de procedimentos, data, horário, nome, confirmação e comandos `MENU` e `ATENDENTE`).
- Envio de respostas pela Graph API (implementado, ver bloqueio abaixo).
- Simulador local do fluxo, que dispensa WhatsApp e credenciais.

Provisório:

- Os horários oferecidos são uma lista fixa (`horarios_disponiveis` em `src/flow.py`).
- A confirmação não grava nada na agenda nem na planilha, por isso a resposta final diz "solicitação recebida" e não "agendado".
- O comando `ATENDENTE` silencia o bot, mas ainda não avisa a diretora.

Pendente:

- Horários livres reais, a partir do `freebusy`, do horário de funcionamento e da duração do procedimento.
- Criação do evento na agenda e registro na planilha.
- Aviso à diretora no atendimento humano.
- Verificação da empresa na Meta e deploy.

## Bloqueio atual: envio pelo número de teste

O recebimento funciona, mas a Meta recusou o envio de respostas pelo número de teste. A causa apontada é a empresa não estar verificada no portfólio empresarial.

- Mensagem de erro registrada: _(colar aqui o texto de `[ERRO ENVIO]` do terminal, sem tokens)_
- Caminho para resolver: verificação da empresa no portfólio da clínica (CNPJ), descrita em "Passagem para produção". O processo depende da Meta e pode levar dias.
- Enquanto isso, o fluxo é desenvolvido e demonstrado com o simulador (`python src/simulador.py`). A chegada das mensagens ao servidor pode ser comprovada no painel local do ngrok (`http://127.0.0.1:4040`).

## Como o sistema funciona

```
Cliente (WhatsApp)
  -> número da Meta
  -> Meta faz POST na URL pública (ngrok, em desenvolvimento)
  -> ngrok repassa para localhost:8000
  -> FastAPI (src/main.py), servido pelo uvicorn
  -> src/flow.py decide a resposta
  -> src/whatsapp.py envia pela Graph API
  -> Meta entrega ao cliente
```

Mais adiante, o `flow.py` também consultará o Google Agenda (`src/calendar_service.py`) e gravará os agendamentos na planilha.

O webhook é uma rota HTTP do próprio backend. A Meta envia um `POST` com um JSON a cada mensagem recebida. O JSON traz o número de quem escreveu (`from`) e o texto (`text.body`), e é esse número que separa as conversas, já que cada requisição chega isolada, sem memória.

Papel de cada ferramenta:

- FastAPI define as rotas do webhook.
- uvicorn é o servidor que executa o FastAPI e escuta a porta 8000.
- ngrok cria uma URL pública `https` que repassa o tráfego para a porta 8000 do computador. A Meta não alcança `localhost`, e o ngrok só existe em desenvolvimento.

Decisões de projeto:

- O Google Agenda é a fonte da verdade da disponibilidade: se o evento existe, o horário está ocupado.
- A planilha (Google Sheets) é apenas cadastro e histórico para a cliente consultar e não influencia os horários oferecidos.
- Não há banco de dados, para reduzir a manutenção após a entrega.
- O estado das conversas fica na memória do processo. Reiniciar o servidor zera as conversas, e a pessoa recomeça pelo menu.

## Estrutura do projeto

```
bot-estetica/
├── .env                       # variáveis de ambiente (não versionado)
├── .env.example               # modelo das variáveis, sem segredos
├── .gitignore
├── requirements.txt
├── credentials/
│   └── google-key.json        # chave da service account (não versionada)
├── data/
│   └── procedimentos.json     # procedimentos, valores e durações
└── src/
    ├── main.py                # servidor FastAPI e rotas do webhook
    ├── flow.py                # máquina de estados da conversa
    ├── whatsapp.py            # envio de mensagens pela Graph API
    ├── calendar_service.py    # consulta de horários ocupados
    └── simulador.py           # conversa local pelo terminal
```

## Primeiros passos (para quem está começando)

### 1. Acessos necessários

Peça à pessoa responsável pelas contas:

| Acesso | Para quê | Como é concedido |
|---|---|---|
| Repositório no GitHub | Código | Convite de colaborador |
| Projeto no Google Cloud | Chave da service account e APIs | Convite no IAM do projeto |
| Agenda de teste do Google Agenda | Criar e editar eventos de teste | Compartilhamento da agenda com a sua conta Google |
| App na Meta for Developers | Token, número de teste e webhook | Convite de função no app, aceito com uma conta pessoal do Facebook |
| Conta própria no ngrok | Túnel de desenvolvimento | Cada pessoa cria a sua (gratuita) |

Quem trabalha apenas no fluxo da conversa (`flow.py`) não precisa de nenhum desses acessos além do repositório: o simulador roda sem credenciais.

### 2. Instalação

Requisitos: Python 3.10 ou superior e Git.

```powershell
git clone <url-do-repositorio>
cd bot-estetica
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

No Linux ou macOS, a ativação é `source .venv/bin/activate`. A ativação vale só para o terminal aberto e deve ser repetida em cada terminal novo.

### 3. Testar o fluxo sem WhatsApp

Da raiz do projeto, com o venv ativo:

```powershell
python src/simulador.py
```

Digite as mensagens como se fosse o cliente (por exemplo, `oi`, depois `1`, `20/10`, `1`, o nome e `SIM`). `MENU` recomeça e `ATENDENTE` silencia o bot. Os procedimentos vêm de `data/procedimentos.json` e são de exemplo.

### 4. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Onde obter | Segredo |
|---|---|---|
| `GOOGLE_KEY_FILE` | Caminho local do JSON da service account (`./credentials/google-key.json`) | O arquivo, sim |
| `CALENDAR_ID` | Google Agenda, configurações da agenda de teste, seção Integrar agenda | Não |
| `PHONE_NUMBER_ID` | Painel da Meta, caso de uso WhatsApp, Configuração da API | Não |
| `WHATSAPP_TOKEN` | Mesma tela, botão Gerar token. Dura poucas horas | Sim |
| `VERIFY_TOKEN` | Texto inventado pela equipe, igual ao informado no cadastro do webhook | Pouco |
| `GRAPH_VERSION` | Versão da Graph API mostrada no exemplo do painel (por exemplo, `v25.0`) | Não |

O `.env` e a pasta `credentials/` estão no `.gitignore`. Depois de alterar o `.env`, reinicie o servidor: o `--reload` do uvicorn observa apenas arquivos `.py`.

### 5. Testar a integração com o Google Agenda

Com o `.env` preenchido e o arquivo `credentials/google-key.json` no lugar:

```powershell
python src/calendar_service.py
```

O resultado é a lista de intervalos ocupados na data consultada, por exemplo `[{'start': '2026-10-14T00:00:00-03:00', 'end': '2026-10-15T00:00:00-03:00'}]`. Rode sempre da raiz do projeto, porque os caminhos do `.env` são relativos a ela.

### 6. Rodar com o WhatsApp

Exige o webhook cadastrado no app da Meta e dois terminais abertos, nesta ordem.

Terminal 1, servidor (venv ativo):

```powershell
uvicorn main:app --app-dir src --reload --port 8000
```

Deve terminar com `Application startup complete`.

Terminal 2, túnel:

```powershell
ngrok http 8000
```

O ngrok exige uma conta e o comando `ngrok config add-authtoken <seu-authtoken>`, executado uma vez. Se ele recusar a versão instalada, rode `ngrok update`. Copie a URL `https` da linha `Forwarding`.

No painel da Meta (Webhooks do WhatsApp):

1. URL de retorno: `<URL do ngrok>/webhook`.
2. Token de verificação: o valor de `VERIFY_TOKEN`.
3. Verificar e salvar e, depois, assinar apenas o campo `messages`.

Um app só aceita uma URL de webhook, ver "Trabalho em equipe".

## Trabalho em equipe

- Cada app da Meta tem uma única URL de webhook. Duas pessoas não conseguem receber mensagens do mesmo número de teste ao mesmo tempo. Combinem quem roda o servidor com o WhatsApp e usem o simulador no restante do tempo.
- O número de teste aceita no máximo 5 destinatários, somando toda a equipe. Cadastrem os telefones de quem realmente vai testar.
- Segredos (token, chave JSON, authtoken do ngrok) nunca vão para o repositório nem para grupos de mensagens. Quando for inevitável compartilhar, usem um gerenciador de senhas ou um canal privado, e prefiram que cada pessoa gere a própria credencial.
- A chave da service account pode ter várias chaves ativas. Cada pessoa pode gerar a sua no Google Cloud, e uma chave comprometida é revogada sem afetar as outras.
- Ao instalar uma biblioteca nova, atualizem a lista com `pip freeze > requirements.txt` e façam o commit.

## Regras de operação da agenda

- Eventos que devem bloquear horário precisam estar marcados como Ocupado. O `freebusy` ignora eventos marcados como Livre, e eventos de dia inteiro costumam vir como Livre por padrão no Google Agenda. Folgas e férias da diretora devem ser cadastradas como Ocupado.
- Fuso horário fixo em `America/Sao_Paulo`, com offset explícito nas datas (`-03:00`), para evitar deslocamento de horários.
- Cancelamentos devem ser feitos pela planilha ou pelo bot, e não apenas no Calendar, para manter o histórico coerente. Os registros usarão uma coluna `status` (`agendado`, `cancelado`, `concluído`) em vez de exclusão de linhas, e uma coluna `event_id` ligando cada linha ao evento correspondente.
- Ordem de gravação prevista: criar o evento no Calendar primeiro e só então registrar na planilha. Assim, uma falha na planilha não deixa o horário aparecendo como livre.

## Segurança e dados pessoais

- `.env` e `credentials/` nunca devem ser versionados. Uma chave commitada permanece no histórico do Git mesmo depois de apagada. Se isso acontecer, a chave deve ser revogada e substituída.
- Em produção, o conteúdo da chave JSON deve ficar em uma variável de ambiente ou secret da plataforma de hospedagem, não em arquivo no servidor.
- Dados pessoais seguem a LGPD e o princípio da necessidade. Para agendar, nome e telefone bastam (o telefone já vem na mensagem do WhatsApp). CPF e endereço só devem ser coletados se a cliente exigir. Para pedir esses campos, descomentar as linhas correspondentes em `CAMPOS`, no `flow.py`. Esses dados ficam somente na planilha, nunca no evento do Calendar.
- O sistema não apaga registros antigos. A cliente deve revisar e remover periodicamente os dados desnecessários, e o acesso à planilha deve ser restrito à cliente e à service account.

## Problemas comuns

- `FileNotFoundError` para `google-key.json`: o arquivo baixado do Google vem com nome longo (`<projeto>-<hash>.json`). Renomear para `google-key.json` ou ajustar `GOOGLE_KEY_FILE`. No Windows, ativar a exibição de extensões para não gerar `.json.json`.
- `[]` no `freebusy`, sem erro: o Google não acusa falha quando a agenda não está acessível. Verificar, nesta ordem, se o ID no `.env` é o da agenda correta, se a agenda está compartilhada com a service account e se o evento está marcado como Ocupado.
- Erro 404 no Calendar: ID da agenda incorreto. Erro 403: Calendar API não ativada no projeto, ou permissão insuficiente.
- `KeyError` ao subir o servidor: falta uma variável no `.env`.
- Erro 190 da Meta (`Session has expired`): o `WHATSAPP_TOKEN` expirou. Gerar outro no painel, atualizar o `.env` e reiniciar o servidor.
- Erro 131030 (`Recipient phone number not in allowed list`): o destinatário não está na lista do painel. Celulares brasileiros chegam no webhook sem o nono dígito, e `normalizar_telefone`, em `whatsapp.py`, o reinsere antes do envio. Se persistir, conferir como o número foi cadastrado na lista.
- A mensagem existe no histórico de webhooks da Meta, mas não chega ao servidor: o app precisa estar inscrito na conta WhatsApp Business, além de assinar o campo `messages`. Para conferir e inscrever (PowerShell, com `$t` contendo o token):

  ```powershell
  curl.exe "https://graph.facebook.com/v25.0/<id-da-conta-whatsapp-business>/subscribed_apps" -H "Authorization: Bearer $t"
  curl.exe -X POST "https://graph.facebook.com/v25.0/<id-da-conta-whatsapp-business>/subscribed_apps" -H "Authorization: Bearer $t"
  ```

- O ngrok recusa a conexão por versão antiga (`ERR_NGROK_121`): rodar `ngrok update`.
- A página de aviso do ngrok ao abrir a URL no navegador não afeta as chamadas da Meta. Basta clicar em Visit Site.

## Passagem para produção

Confirmar cada etapa no painel da Meta, pois os requisitos e os nomes das telas mudam com frequência.

1. A clínica cria o portfólio empresarial dela (Meta Business) e o verifica com os documentos da empresa (CNPJ). O portfólio de teste atual não deve ser verificado com dados pessoais.
2. O app e a conta WhatsApp Business ficam vinculados ao portfólio da clínica, com a diretora como administradora e a equipe com função de desenvolvedor.
3. Registrar o número real da clínica, o que gera um novo `phone_number_id`.
4. Gerar um token permanente (System User no Business Manager) e colocar o app em modo Live.
5. Atualizar as variáveis de ambiente e refazer o deploy. O código não precisa mudar: o que varia entre teste e produção (`PHONE_NUMBER_ID`, `WHATSAPP_TOKEN`, `CALENDAR_ID`) está no `.env`.
6. Google Cloud: adicionar a conta Google da cliente como proprietária do projeto ou recriá-lo na conta dela, gerando nova chave.
7. Hospedar o backend em plataforma com plano gratuito adequado. Planos que suspendem o serviço por inatividade podem atrasar a primeira resposta, e algumas plataformas exigem cartão cadastrado.
8. Conferir se `normalizar_telefone` continua necessário com o número real e removê-lo se não for.

## Custos

- Desenvolvimento: sem custo (número de teste, Calendar API, Sheets API, ngrok gratuito e execução local).
- Produção: respostas enviadas dentro da janela de 24 horas após o contato do cliente não são cobradas. Mensagens iniciadas pela empresa (lembretes, por exemplo) usam templates pagos, e o chip do número e a hospedagem fora do plano gratuito também podem gerar custo. Conferir a tabela de preços vigente da Meta.

## Próximos passos

1. Resolver o bloqueio de envio (verificação da empresa).
2. Geração de horários livres a partir do `freebusy`, do horário de funcionamento e da duração do procedimento.
3. Criação do evento na agenda e registro na planilha.
4. Aviso à diretora no atendimento humano.
5. Deploy e atualização deste documento com o procedimento de ativação.
