# Estrutura sugerida para o relatório académico

Cada secção indica de onde tirar o conteúdo e as evidências já geradas.

1. **Introdução e objetivos.** Problema da priorização em urgências; um agente baseado em utilidade; âmbito
   académico e limitações éticas (dados sintéticos, sem uso clínico).
2. **Enquadramento teórico.** Agentes inteligentes e os 5 tipos (simples, baseado em modelo, em objetivos, em
   utilidade, com aprendizagem); porque a utilidade permite compromisso entre critérios conflitantes; teoria de
   utilidade multi-atributo (soma ponderada).
3. **Especificação PEAS.**

   | | |
   |---|---|
   | Performance | Prioridade coerente com a utilidade; determinismo; esperas por gravidade (métricas das simulações); explicação em cada decisão |
   | Environment | Serviço de urgência simulado: pacientes que chegam, recursos limitados (médicos, camas, oxigénio), tempo |
   | Actuators | Reordenar a fila, escolher e chamar o próximo paciente, registar decisão e justificação |
   | Sensors | Dados dos pacientes (idade, sinais vitais, sintomas), recursos livres, relógio |

   Propriedades do ambiente: parcialmente observável (só os dados registados), dinâmico, sequencial, discreto e
   determinístico dado o relógio e a configuração.
4. **Arquitetura.** `docs/ARQUITETURA.md`: camadas, ciclo de decisão, modelo ER, API.
5. **Função de utilidade.** Fórmula, normalização, justificação de cada fator e dos pesos (tabela da secção 3 da
   arquitetura). Decisões de desenho: saturação da espera, proteção de recursos, desempate.
6. **Implementação.** Tecnologias, estrutura de pastas, fila dinâmica (nota sobre heapq), persistência e histórico.
7. **Simulação e metodologia experimental.** Perfis de pacientes, cenários, seeds, métricas. Fonte:
   `app/simulation/` e `backend/reports/RELATORIO_EXPERIENCIAS.md`.
8. **Resultados.** Figuras E1 a E6 e tabelas do relatório de experiências; comparação de configurações de pesos.
9. **Testes.** 62 testes automáticos (utilidade, fila, API, simulação, determinismo); comando `pytest -v`.
10. **Discussão, limitações e ética.** Parâmetros experimentais, ausência de validação clínica, risco de falsos
    negativos num sistema real, viés dos pesos escolhidos, privacidade (dados sintéticos).
11. **Conclusão e trabalho futuro.** Aprender pesos a partir de dados, validação com especialistas, protocolos
    reais, autenticação, escalabilidade.
12. **Referências.** Russell & Norvig, *Artificial Intelligence: A Modern Approach*; documentação de FastAPI,
    SQLAlchemy, SimPy, Next.js.

Divisão por membros do grupo (sugestão): agente e testes · API e base de dados · simulação e experiências · frontend ·
relatório e demonstração.
