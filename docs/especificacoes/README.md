# Especificações do experimento

Requisitos formais escritos **antes** da implementação, no formato
[OpenSpec](https://github.com/Fission-AI/OpenSpec) (`SHALL` / `WHEN` / `THEN`).

Valem menos como documentação do que o código faz — para isso, veja
`docs/02-arquitetura-do-codigo.md` — e mais como registro **da intenção**: explicam por que
decisões que parecem arbitrárias no código foram tomadas.

| Especificação | O requisito |
|---|---|
| `cumulative-map-degradation/` | Os bloqueios são cumulativos (10% → 20% → 30%) e reprodutíveis por semente. |
| `fixed-pair-selection/` | Os pares origem–destino são fixados uma vez, para permitir comparação pareada. |
| `dijkstra-baseline/` | O A\* com `h = 0` é medido, para dar um baseline de expansões. |
| `multi-seed-reproducibility/` | O experimento roda com 5 sementes. |
| `comprehensive-robustness-logging/` | O log é caso a caso, não agregado — foi o que tornou possível toda a reanálise de agosto. |
| `synthesis-metrics-tracking/` | Tempo e aptidão da síntese são registrados. |
| `degradacao-conectividade/` | Protocolo v2 (nov/2026): extremos protegidos (R1), conectividade preservada (R2), meta e rejeições registradas (R3), pares validados em cada nível. |

`_propostas-arquivadas/` traz as duas propostas de mudança (março/2026) com sua justificativa,
seu desenho e sua lista de tarefas.

> Note que `fixed-pair-selection` foi implementado de forma que gerou a limitação P2: os pares
> são fixados **no estado de 30% de bloqueio** e reusados nos três níveis. A especificação pedia
> pares fixos; a implementação os fixou no lugar errado.
>
> Resolvido no protocolo v2 (`degradacao-conectividade/`, `codigo/robustez-2026-11/`): os pares
> são validados em cada nível e, com R1 e R2, são todos os pares conectados no mapa original.
