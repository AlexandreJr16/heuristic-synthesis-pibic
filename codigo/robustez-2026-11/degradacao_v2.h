#pragma once
#include "../medicoes-2026-08/comum.h"

/*
 - Grupo: estado
   aplicaRegras: liga R1 e R2; desligado, os mecanismos v2 reproduzem o map.cpp de marco
   rejeitadasR1: celulas distintas recusadas por serem origem ou destino de par
   rejeitadasR2: celulas distintas recusadas por dividir uma componente conexa
   tentativasR1, tentativasR2: tentativas recusadas (a mesma celula conta a cada sorteio)
   chamadasBfs, celulasBfs: custo do teste global de conectividade
 - Grupo: regras
   protegeExtremos: marca origem e destino de todos os pares do cenario (R1)
   bloqueia: bloqueia a celula se R1 e R2 permitirem
   celulaRecusada: a celula foi recusada por R1 ou R2 desde o ultimo degradaNiveis
 - Grupo: padroes
   Padrao: nome, gerador de marco (map.cpp) e gerador v2, com os mesmos parametros e sorteios
   PADROES: os 5 padroes na ordem de main.cpp:197-202
   NIVEIS: 10, 20 e 30% das celulas livres do mapa original
   Nivel: grid de um nivel, % atingido, celulas e tentativas recusadas acumuladas ate ele
   degradaNiveis: srand(semente) e degradacao cumulativa 10 -> 20 -> 30 a partir do original
 - Grupo: verificacao
   hashGrid: FNV-1a do grid atual
   paresConectados: indices dos pares com origem e destino na mesma componente do grid atual
   verificaNivel: aborta se R1, R2, a cumulatividade ou a conectividade dos pares falharem
 - Grupo: amostra
   formulaDoMapa: formula de marco do mapa em dados/resultados_sintese.csv (1a ocorrencia, P7)
   amostraTreino: pares da amostra de aptidao do AG (main.cpp:108-117, srand(42))
*/

extern bool aplicaRegras;
extern long long rejeitadasR1, rejeitadasR2, tentativasR1, tentativasR2, chamadasBfs, celulasBfs;

void protegeExtremos(const vector<ScenProblem> &scen);
bool bloqueia(int x, int y);
bool celulaRecusada(int x, int y);

struct Padrao { string nome; void (*v1)(int); void (*v2)(int); };
extern const vector<Padrao> PADROES;
extern const vector<double> NIVEIS;

struct Nivel { vector<vector<bool>> grid; double pct; long long r1, r2, t1, t2; };
vector<Nivel> degradaNiveis(void (*degrada)(int), int semente, bool metaAbsoluta,
                            const vector<vector<bool>> &original);

uint64_t hashGrid();
vector<int> paresConectados(const vector<ScenProblem> &scen);
vector<int> verificaNivel(const vector<vector<bool>> &anterior, const vector<vector<int>> &compOriginal,
                          int nCompOriginal, const vector<ScenProblem> &scen,
                          const vector<int> &paresOriginal, const string &contexto);

string formulaDoMapa(const string &mapa);
vector<char> amostraTreino(int n);
