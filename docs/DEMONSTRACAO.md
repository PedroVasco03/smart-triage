# Roteiro da demonstração académica (cerca de 10 minutos)

## Antes de começar
MySQL ligado, backend em :8000, frontend em :3000. Na página **Agente** confirma a configuração v1 (40/20/30/10).
Se quiseres partir de zero, apaga e recria a base `smart_triage`.

## Passo a passo

| Min | Onde | O que fazer | O que dizer |
|---|---|---|---|
| 0-1 | Painel | Mostrar o painel vazio | Um único agente baseado em utilidade; dados sintéticos; não é triagem clínica |
| 1-3 | Simulação > Fila ao vivo | Gerar 8 pacientes; abrir **Fila** | A fila é ordenada pela utilidade U; a barra mostra o contributo de cada fator |
| 3-5 | Fila > detalhe de um paciente | Mostrar fatores, pesos, contributos e explicação | O agente explica a decisão; nada é caixa preta |
| 5-6 | Fila | **Avançar 15 min** duas ou três vezes | A espera sobe e satura; a ordem muda; o histórico regista porquê |
| 6-7 | Agente | Passar para "Espera primeiro" e guardar | Nova versão, fila recalculada; aviso de que a espera pode superar a gravidade |
| 7-8 | Fila > painel Recursos | Reduzir "Médico" para 1, chamar dois pacientes; depois aumentar o recurso ou concluir um atendimento | Os recursos são ocupados e libertados; quem está em risco não perde prioridade por falta deles, só não é chamado |
| 8-10 | Simulação > Comparar pesos | Executar a comparação | Mesma seed: as diferenças vêm só dos pesos |

Fecha com os gráficos de `backend/reports/` (E1 a E6) e com a limitação: resultados experimentais, sem validação clínica.

## Perguntas prováveis e respostas curtas

- **Os pacientes gerados são feitos por IA?** Não. "Gerar pacientes" sorteia dados a partir de perfis estatísticos (com
  seed) para termos dados sintéticos. A IA é o agente que os prioriza.
- **O que acontece quando os recursos acabam?** A fila avisa; os pacientes ficam "Sem recursos" mas mantêm a posição;
  os recursos voltam quando um atendimento termina (sozinho, à mão ou ao avançar o tempo) ou quando se aumenta a
  capacidade no painel de Recursos.

- **Isto é IA ou só regras?** É um agente baseado em utilidade (Russell & Norvig): avalia alternativas com uma função
  de utilidade multifator e escolhe a de maior utilidade. Não há `if/else` por gravidade. A função é explícita,
  configurável e testada.
- **Não aprende?** Não, e foi decisão do projeto: o agente é só de utilidade. Os pesos são parâmetros ajustáveis e
  as experiências mostram a sensibilidade. Aprender os pesos a partir de dados seria trabalho futuro.
- **Porque é que a espera não pode ultrapassar a gravidade?** E satura e o seu peso é limitado; a experiência E5 mostra
  a espera necessária em função do peso. O sistema avisa quando w2 ≥ w1.
- **E se faltarem recursos?** A prioridade mantém-se (fator A protegido por max(G, R)); a seleção do próximo paciente
  é que respeita os recursos livres.
- **É reprodutível?** Sim: relógio injetável, desempate determinístico e simulações com seed.
- **Pode usar-se num hospital?** Não. Dados sintéticos, parâmetros experimentais e sem validação clínica.
- **Porque heapq se recalculam tudo?** As prioridades mudam todas com o tempo; recalcular e ordenar é mais simples e
  correto. O heap serve para o top-k e para escolher o próximo atendível.
