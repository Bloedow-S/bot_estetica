# Bot de agendamento via WhatsApp para clínica de estética

Projeto acadêmico. Chatbot de WhatsApp que informa dias, horários e valores dos procedimentos de uma clínica de estética e registra agendamentos, consultando a disponibilidade no Google Agenda da diretora. Usa a WhatsApp Cloud API (Meta) e a Google Calendar API.

O produto será entregue à cliente sem manutenção posterior. Isso orienta as decisões de projeto descritas abaixo: poucas dependências, contas e credenciais sob propriedade da cliente e nenhum servidor de banco de dados para administrar.

## Status

Concluído:

- Estrutura do projeto Python com ambiente virtual.
- Consulta de horários ocupados no Google Agenda (`freebusy`) por meio de service account.

Pendente:

- Webhook para receber mensagens (FastAPI) e envio de respostas pela Graph API.
- Fluxo de conversa (estado por número de telefone).
- Cálculo de horários livres conforme a duração de cada procedimento.
- Criação do evento na agenda ao confirmar o agendamento.
- Registro dos agendamentos em planilha.
- Deploy.

## Arquitetura

```
WhatsApp -> Meta Cloud API -> webhook (backend Python) -> Google Calendar API
                                        |
                                        +-> Google Sheets (registro dos agendamentos)
```

O webhook é uma rota HTTP do próprio backend. A Meta envia um `POST` com um JSON a cada mensagem recebida, e o backend responde chamando a Graph API. O JSON traz, entre outros campos, o número de quem escreveu (`from`) e o texto (`text.body`), e é esse número que separa as conversas.

Decisões de projeto:

- **Google Agenda** é a fonte da verdade da disponibilidade. Se o evento existe, o horário está ocupado.
- **Planilha (Google Sheets)** é apenas cadastro e histórico para a cliente consultar. Não influencia os horários oferecidos.
- Não há banco de dados, para reduzir a manutenção após a entrega.

## Estrutura do projeto

```
bot-estetica/
├── .env                       # variáveis de ambiente (não versionado)
├── .gitignore
├── requirements.txt
├── credentials/
│   └── google-key.json        # chave da service account (não versionada)
└── src/
    └── calendar_service.py    # consulta de horários ocupados
```

## Configuração local

Requisitos: Python 3.10 ou superior e Git.

1. Criar e ativar o ambiente virtual (Windows):

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

   No Linux ou macOS: `source .venv/bin/activate`. A ativação vale apenas para o terminal aberto, então deve ser repetida em cada terminal novo.

2. Instalar as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

   Ao instalar uma biblioteca nova, atualizar a lista com `pip freeze > requirements.txt`.

3. Obter a chave da service account no Google Cloud (IAM e administrador, Contas de serviço, aba Chaves, Adicionar chave, JSON). Salvar o arquivo como `credentials/google-key.json`.

4. Compartilhar a agenda com o e-mail da service account (`<nome>@<id-do-projeto>.iam.gserviceaccount.com`), com permissão para fazer alterações em eventos.

5. Criar o arquivo `.env` na raiz:

   ```
   GOOGLE_KEY_FILE=./credentials/google-key.json
   CALENDAR_ID=<id-da-agenda>@group.calendar.google.com
   ```

   O ID da agenda fica em Configurações da agenda, seção Integrar agenda.

6. Executar o teste, sempre a partir da raiz do projeto (os caminhos do `.env` são relativos a ela):

   ```powershell
   python src/calendar_service.py
   ```

   O resultado é a lista de intervalos ocupados na data consultada, por exemplo `[{'start': '2026-10-14T00:00:00-03:00', 'end': '2026-10-15T00:00:00-03:00'}]`.

### Problemas comuns

- `FileNotFoundError` para `google-key.json`: o arquivo baixado do Google vem com nome longo (`<projeto>-<hash>.json`). Renomear para `google-key.json` ou ajustar `GOOGLE_KEY_FILE`. No Windows, ativar a exibição de extensões para não gerar `.json.json`.
- Retorno `[]` sem erro: o `freebusy` não acusa falha quando a agenda não está acessível. Verificar, nesta ordem, se o ID no `.env` é o da agenda correta, se a agenda está compartilhada com a service account e se o evento está marcado como Ocupado.
- Erro 404: ID da agenda incorreto.
- Erro 403: Calendar API não ativada no projeto do Google Cloud, ou permissão insuficiente.

## Regras de operação da agenda

- Eventos que devem bloquear horário precisam estar marcados como **Ocupado**. O `freebusy` ignora eventos marcados como Livre, e eventos de dia inteiro costumam vir como Livre por padrão no Google Agenda. Folgas e férias da diretora devem ser cadastradas como Ocupado.
- Fuso horário fixo em `America/Sao_Paulo`, com offset explícito nas datas (`-03:00`), para evitar deslocamento de horários.
- Cancelamentos devem ser feitos pela planilha ou pelo bot, e não apenas no Calendar, para manter o histórico coerente. Os registros usarão uma coluna `status` (`agendado`, `cancelado`, `concluído`) em vez de exclusão de linhas, e uma coluna `event_id` ligando cada linha ao evento correspondente.
- Ordem de gravação prevista: criar o evento no Calendar primeiro e só então registrar na planilha. Assim, uma falha na planilha não deixa o horário aparecendo como livre.

## Segurança e dados pessoais

- `.env` e `credentials/` estão no `.gitignore` e nunca devem ser versionados. Uma chave commitada permanece no histórico do Git mesmo depois de apagada. Compartilhar a chave entre a equipe por canal separado do repositório.
- Em produção, o conteúdo da chave JSON deve ficar em uma variável de ambiente ou *secret* da plataforma de hospedagem, não em arquivo no servidor.
- Dados pessoais seguem a LGPD e o princípio da necessidade: coletar apenas o indispensável. Para agendar, nome e telefone bastam (o telefone já vem na mensagem do WhatsApp). CPF e endereço só devem ser coletados se a cliente exigir e, nesse caso, ficam somente na planilha, nunca no evento do Calendar.
- O sistema não apaga registros antigos. A cliente deve revisar e remover periodicamente os dados que não forem mais necessários, e o acesso à planilha deve ser restrito à cliente e à service account.

## Ambiente de teste da Meta

- Número de teste fornecido pela Meta, que só troca mensagens com até 5 destinatários cadastrados no painel.
- O token de acesso temporário expira em 24 horas e precisa ser regenerado no painel.
- Em desenvolvimento, o webhook é exposto com ngrok. No plano gratuito a URL pública muda a cada reinício, e o endereço cadastrado no painel da Meta precisa ser atualizado.

Todo valor que muda entre teste e produção (`PHONE_NUMBER_ID`, `WHATSAPP_TOKEN`, `CALENDAR_ID`) fica em variável de ambiente. O código não precisa ser alterado na passagem para produção.

## Passagem para produção

Confirmar cada etapa no painel da Meta, pois os requisitos e os nomes das telas mudam com frequência.

1. A clínica cria o portfólio empresarial dela (Meta Business) e o verifica com os documentos da empresa (CNPJ). O portfólio de teste atual não deve ser verificado com dados pessoais.
2. O app e a conta WhatsApp Business ficam vinculados ao portfólio da clínica, com a diretora como administradora.
3. Registrar o número real da clínica, o que gera um novo `phone_number_id`.
4. Gerar um token permanente (System User no Business Manager) e colocar o app em modo Live.
5. Atualizar as variáveis de ambiente e refazer o deploy.
6. Google Cloud: adicionar a conta Google da cliente como proprietária do projeto ou recriá-lo na conta dela, gerando nova chave.
7. Hospedar o backend em plataforma com plano gratuito adequado. Planos que suspendem o serviço por inatividade podem atrasar a primeira resposta. Verificar também se a plataforma exige cartão cadastrado.

## Custos

- Desenvolvimento: sem custo (número de teste, Calendar API, Sheets API e execução local).
- Produção: respostas enviadas dentro da janela de 24 horas após o contato do cliente não são cobradas. Mensagens iniciadas pela empresa (lembretes, por exemplo) usam templates pagos, e o chip do número e a hospedagem fora do plano gratuito também podem gerar custo. Conferir a tabela de preços vigente da Meta.

## Próximos passos

1. Webhook com FastAPI (`GET` de verificação e `POST` de mensagens) e função de envio pela Graph API.
2. Geração de horários livres a partir do `freebusy`, do horário de funcionamento e da duração do procedimento.
3. Fluxo de conversa com estado por telefone e palavra-chave para atendimento humano.
4. Criação do evento e registro na planilha.
5. Deploy e atualização deste documento com o procedimento de ativação.