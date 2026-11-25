# Smart Triage

**Agente inteligente baseado em utilidade para triagem e priorização de pacientes em serviços de urgência.**
Projeto académico de Inteligência Artificial. Usa apenas dados sintéticos. As pontuações são parâmetros
experimentais de simulação: **não são triagem clínica, nem diagnóstico, nem substituem profissionais de saúde.**

Stack: Next.js + TypeScript + Tailwind + shadcn/ui (estilo) + Recharts · FastAPI + Pydantic · SQLAlchemy + MySQL · NumPy/Pandas/heapq/SimPy.

---

## 1. Requisitos no Mac (Apple Silicon, Homebrew em /opt/homebrew)

```bash
brew install mysql        # salta se já tens MySQL
brew services start mysql
/opt/homebrew/bin/python3.12 --version   # as dependências atuais exigem Python 3.12 ou superior
                                         # se não existir: brew install python@3.12
node --version                           # o Next 16 exige Node 20.9 ou superior
                                         # se for mais antigo ou não existir: brew install node
```

Cria a base de dados e o utilizador (troca `CHANGE_ME` por uma senha tua):

```bash
mysql -u root
```
```sql
CREATE DATABASE smart_triage CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE smart_triage_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'triage_user'@'localhost' IDENTIFIED BY 'CHANGE_ME';
GRANT ALL PRIVILEGES ON smart_triage.* TO 'triage_user'@'localhost';
GRANT ALL PRIVILEGES ON smart_triage_test.* TO 'triage_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Se o `mysql -u root` pedir senha, usa `mysql -u root -p` com a senha que definiste.

Versões fixadas (as mais recentes à data, testadas): FastAPI 0.163.1, SQLAlchemy 2.1.8, Pydantic 2.14.3, Alembic 1.20.1,
NumPy 2.5.4, Pandas 3.1.1, SimPy 4.1.2, Next.js 16.4.6, React 19.3.1, Tailwind CSS 4.3.5, Recharts 3.10.1, TypeScript 7.0.2.
Ficheiros: `backend/requirements.txt` e `frontend/package.json`.

## 2. Backend (porta 8000)

```bash
cd smart-triage/backend
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `backend/.env` e põe a tua senha em `DATABASE_URL`:

```
DATABASE_URL=mysql+pymysql://triage_user:CHANGE_ME@127.0.0.1:3306/smart_triage
```

Arranca (as tabelas, a configuração v1 e os recursos iniciais são criados no arranque):

```bash
uvicorn main:app --reload --port 8000
```

Swagger/OpenAPI: http://localhost:8000/docs

Alternativa com migrações Alembic (em vez de `AUTO_CREATE_TABLES`): põe `AUTO_CREATE_TABLES=false` no `.env` e corre
`alembic upgrade head` antes de arrancar.

## 3. Frontend (porta 3000)

```bash
cd smart-triage/frontend
npm install
cp .env.local.example .env.local     # BACKEND_URL=http://127.0.0.1:8000
npm run dev
```

Arranca **primeiro o backend** e depois o frontend. Abre **http://localhost:3000**.

O browser fala só com o Next (pedidos a `/backend/*`, reenviados para o FastAPI), por isso não há problemas de CORS
e o sistema funciona abra-se por `localhost`, `127.0.0.1` ou pelo IP da rede.

Para a demonstração, o modo produção é mais estável e rápido:

```bash
npm run build
npm start
```

Se a 3000 ou a 8000 estiverem ocupadas por outro projeto, muda a porta (`npm run dev -- -p 3001`,
`uvicorn main:app --port 8001`) e ajusta `BACKEND_URL` em `frontend/.env.local`.

### Resolução de problemas

| Sintoma | Causa e solução |
|---|---|
| Página desenhada mas formulários e botões não respondem; aparece um aviso vermelho "A interface não arrancou" | O JavaScript não carregou. Pára o frontend (Ctrl+C), corre `rm -rf .next`, arranca outra vez com `npm run dev` e abre `http://localhost:3000`. Confirma que `npm install` terminou sem erros. |
| "Não consegui falar com o backend" | O backend não está a correr. No terminal do backend: `source .venv/bin/activate && uvicorn main:app --port 8000`. Testa `http://127.0.0.1:8000/health`. |
| `Access denied` ou `Can't connect to MySQL` no backend | Confere `DATABASE_URL` em `backend/.env` (utilizador, senha, base) e que o MySQL está ativo: `brew services list`. Se a senha tiver `#`, `@` ou `/`, escreve-a codificada (`#` = `%23`). |
| `ModuleNotFoundError` no backend | O venv não está ativo ou foi criado com Python antigo: `source .venv/bin/activate`; Python 3.12 ou superior. |
| `Unknown column 'service_minutes'` (base criada por uma versão anterior) | Reinicia o backend: com `AUTO_CREATE_TABLES=true` a coluna é acrescentada sozinha. Se usas Alembic: `alembic upgrade head`. |
| `address already in use` | Outra aplicação usa a porta. Muda a porta como indicado acima. |

## 4. Testes

```bash
cd smart-triage/backend && source .venv/bin/activate
pytest -v                                   # 61 testes em SQLite em memória (+1 teste que só corre em MySQL)
export TEST_MYSQL_URL="mysql+pymysql://triage_user:CHANGE_ME@127.0.0.1:3306/smart_triage_test"
pytest -v                                   # repete tudo em MySQL real (apaga e recria as tabelas da base de teste)
                                            # (este projeto foi verificado em MySQL 8.0: 62 testes a passar)
```

## 5. Experiências e relatório de resultados

```bash
cd smart-triage/backend && source .venv/bin/activate
python -m scripts.run_experiments            # gera backend/reports/ (CSV, gráficos PNG e RELATORIO_EXPERIENCIAS.md)
```

Para perceber o funcionamento completo (o que é IA e o que não é, ciclo de vida do paciente, recursos), lê `docs/FUNCIONAMENTO.md`.

Já incluí uma execução em `backend/reports/` (5 seeds). As experiências cobrem: espera, gravidade, risco por idade,
recursos, sensibilidade aos pesos e 5 cenários × 3 configurações de pesos.

## 6. Demonstração sugerida

1. **Simulação > Fila ao vivo**: gerar 8 pacientes. **Fila**: ver a ordem, a barra de contributos e o botão do detalhe.
2. Abrir um paciente: tabela de fatores, pesos, contributo, explicação, evolução.
3. **Fila > Avançar 15 min** várias vezes: a espera sobe e a ordem muda; ver o histórico no detalhe.
4. **Agente**: passar para "Espera primeiro", guardar: a fila é recalculada e nasce a versão 2.
5. **Fila > painel Recursos**: reduzir "Médico" para 1, chamar dois pacientes e ver a faixa "Ninguém pode ser chamado agora";
   aumentar o recurso ou concluir um atendimento e chamar de novo. Pacientes bloqueados ficam "Sem recursos" sem perderem posição.
6. **Simulação > Comparar pesos**: mesmo cenário e seed com 3 configurações; gráfico da espera por gravidade.

---

## 7. O agente

Ciclo: **Perceção** (pacientes, recursos livres, instante) → **Processamento** (fatores G, E, R, A em 0..100) →
**Avaliação** (U de cada paciente + explicação) → **Seleção** (ordem por U com desempate determinístico e escolha do
próximo atendível respeitando recursos) → **Ação** (persistir fila, pontuações, histórico) → **Reavaliação** (novo ciclo
a cada evento relevante). O agente (`backend/app/agents/`) é puro: não acede à BD nem à API.

### Função de utilidade

```
U(p) = (w1·G + w2·E + w3·R + w4·A) / (w1 + w2 + w3 + w4)          pesos por defeito 40 / 20 / 30 / 10
G = a·V + (1−a)·S         V = m·max(dᵢ) + (1−m)·média(dᵢ)         S = 10 · severidade máxima dos sintomas
E = 100·(1 − e^(−t/τ))    satura: nunca chega a 100 (τ = 60 min)
R = 0,5·max(dᵢ) + 0,3·F_idade + 0,2·S       F_idade em U (crianças pequenas e idosos)
A = A_raw + (100 − A_raw)·max(G, R)/100     A_raw = % das necessidades de recursos cobertas
```

`dᵢ` é o desvio (0..100) de cada sinal vital face ao intervalo de referência experimental.

Decisões de desenho que alteram ligeiramente o prompt original:

- **A (recursos) protegido**: com a soma simples, a falta de recursos baixaria a prioridade de quem está em risco. A
  fórmula acima faz com que quanto maior max(G, R), menor a penalização.
- **E satura e tem teto de peso**: com os pesos por defeito a espera dá no máximo 20 pontos, o que só compensa
  diferenças de G inferiores a 50 pontos. O ecrã do agente avisa quando w2 ≥ w1.
- **heapq**: como todas as chaves mudam com o tempo, a fila é recalculada e reordenada a cada ciclo (O(n log n)).
  O heap é usado para `top_k` e para a seleção do próximo atendível.
- **Desempate**: U ↓, G ↓, R ↓, hora de chegada ↑, id ↑. Mesmos dados e configuração dão sempre a mesma ordem.
- **GET /queue reavalia na leitura** (a espera depende do relógio) e só grava um novo snapshot quando a ordem ou a
  configuração mudam.
- **Tabelas acrescentadas**: `agent_configurations` (versões), `patient_resource_requirements`,
  `patient_status_history`, `queue_entries`.
- **Simulação**: motor SimPy com relógio virtual que usa o mesmo agente. Pacientes simulados ficam com `session_id` e
  não aparecem na fila real.

## 8. Estrutura

```
smart-triage/
├── backend/
│   ├── main.py
│   ├── app/
│   │   ├── agents/       base_agent.py, utility_agent.py, domain.py
│   │   ├── services/     utility_service (fórmula), priority_service (fila), patient/config/resource/simulation/statistics
│   │   ├── api/          routers REST
│   │   ├── schemas/      Pydantic (unidades e intervalos documentados)
│   │   ├── models/       SQLAlchemy (12 tabelas)
│   │   ├── database/     sessão, init_db
│   │   ├── simulation/   generators, scenarios, engine (SimPy)
│   │   └── core/         config, clock, errors
│   ├── alembic/          migração inicial
│   ├── scripts/          run_experiments.py (relatório de experiências)
│   ├── reports/          resultados gerados (CSV, PNG, Markdown)
│   └── tests/            utilidade, fila, API, experiências, MySQL
├── docs/                 ARQUITETURA.md, DEMONSTRACAO.md, RELATORIO_ESTRUTURA.md
└── frontend/
    ├── app/              /, /queue, /queue/[id], /patients, /patients/new, /agent, /simulation
    ├── components/       ui (estilo shadcn), charts, utility-bar, session-view
    ├── services/  hooks/  types/  lib/
```

## 9. Limitações (para o relatório)

- Dados e intervalos de referência são sintéticos/experimentais; o modelo reflete os pesos que o grupo define.
- Sem autenticação nem controlo de acessos (fora do âmbito académico).
- Os resultados da simulação mostram o comportamento do agente, não validade clínica.
