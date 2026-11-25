# Como o sistema funciona (visão completa)

## 1. O que é IA aqui e o que não é

| Parte | O que faz | É IA? |
|---|---|---|
| **Agente de utilidade** (`backend/app/agents/`) | Calcula a utilidade U(p) de cada paciente, ordena a fila e escolhe quem é chamado a seguir, com explicação | **Sim: é o agente inteligente do projeto** |
| **Gerar pacientes fictícios** (`simulation/generators.py`) | Sorteia idade, sinais vitais e sintomas a partir de perfis estatísticos (NumPy, com seed) | **Não.** É amostragem aleatória para ter dados sintéticos |
| **Simulação** (`simulation/engine.py`, SimPy) | Simula chegadas, recursos e atendimentos no tempo e chama o agente em cada evento | Não: é o ambiente onde o agente é testado |
| Interface, API, base de dados | Mostram, validam e guardam | Não |

Não há modelos de linguagem nem aprendizagem automática. O agente não aprende: decide com uma função explícita,
configurável e testada.

## 2. Vida de um paciente

```
Registar ──► EM ESPERA ──(Chamar próximo)──► EM ATENDIMENTO ──► ATENDIDO
 (ou gerar)      │ na fila, a espera sobe        │ ocupa recursos         (recursos libertados)
                 └─(Remover/Sair)─► SAIU         └─ termina: sozinho (duração prevista),
                                                    à mão (Concluir atendimento) ou ao avançar o tempo
```

- **Registar:** dados sintéticos; opcionalmente os recursos que precisa e a duração prevista do atendimento.
- **Em espera:** o agente reavalia a fila sempre que algo muda (novo paciente, dados, estado, recursos, pesos, tempo).
- **Chamar próximo:** o agente escolhe o paciente de maior utilidade **que consegue ser atendido com os recursos livres**.
  Quem está à frente mas não tem recursos fica marcado "Sem recursos" e **não perde posição**.
- **Em atendimento:** ocupa os recursos de que precisa (ex.: 1 médico, 1 cama).
- **Terminar:** (a) sozinho, quando passa a duração prevista; (b) à mão, em "Concluir atendimento"; (c) ao "Avançar
  tempo", que também faz avançar os atendimentos em curso. Ao terminar, os recursos voltam a ficar livres e a fila é
  reavaliada.

## 3. Recursos

Cada recurso tem **total** (`quantity_available`), **em uso** (`quantity_in_use`) e **livre** (total − em uso).

- Ocupar: ao chamar o paciente. Libertar: ao terminar o atendimento.
- **Aumentar ou diminuir o total** e **adicionar um novo tipo de recurso**: painel "Recursos do serviço", na página
  **Fila** (e também em **Agente**). Não dá para baixar o total abaixo das unidades em uso.
- Se faltam recursos a todos os pacientes em espera, aparece uma faixa na Fila com a saída: concluir um atendimento ou
  aumentar recursos.
- Na fórmula, o fator A mede a cobertura dos recursos necessários, protegido pelo risco: quem tem G ou R altos quase
  não perde utilidade por falta de recursos.

## 4. Tempo

A espera usa o relógio real. "Avançar 15 min" acelera a demonstração: recua a hora de chegada de quem espera e a hora
de início de quem está em atendimento. Na simulação (SimPy) o tempo é virtual e cada paciente tem a sua duração.

## 5. Onde está cada coisa

| Quero… | Onde |
|---|---|
| Ver a ordem e porquê | Fila, e clicar no código do paciente (detalhe da decisão) |
| Chamar, concluir, avançar tempo, gerar pacientes | Fila |
| Ver e alterar recursos, adicionar um recurso novo | Fila (painel "Recursos do serviço") ou Agente |
| Mudar pesos e parâmetros | Agente |
| Testar cenários e comparar pesos | Simulação |
| Resultados e gráficos para o relatório | `backend/reports/` e Simulação |

## 6. Limitações

- Parâmetros clínicos (intervalos, idade) são experimentais; sem validação clínica; dados sintéticos.
- O agente não aprende; os pesos são escolhidos por nós.
- A duração do atendimento é um valor fixo por paciente (na simulação é sorteada por perfil).
- Sem autenticação.
