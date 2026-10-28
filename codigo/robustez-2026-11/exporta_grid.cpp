// Grid de um (mapa, semente, padrao) a 30%, no v1 e no v2, para as figuras do notebook.
// '@' obstaculo original, '.' livre, '#' bloqueada pela degradacao,
// 'o' recusada por R2 e livre (passagem), 'r' recusada por R1 (extremo de par)
#include "degradacao_v2.h"

static void grava(const string &arq, const vector<vector<bool>> &original, const set<pair<int, int>> &extremos,
                  bool marcaRecusadas) {
  ofstream f(arq, ios::trunc);
  for (int i = 0; i < height; i++) {
    for (int j = 0; j < width; j++) {
      char c = !original[i][j] ? '@' : !grid[i][j] ? '#' : '.';
      if (c == '.' && marcaRecusadas && celulaRecusada(i, j)) c = extremos.count({i, j}) ? 'r' : 'o';
      f << c;
    }
    f << "\n";
  }
  if (!f) {
    cerr << "falha ao gravar " << arq << endl;
    exit(6);
  }
}

int main(int argc, char **argv) {
  if (argc < 5) {
    cerr << "uso: exporta_grid <mapa> <semente> <padrao> <saida>" << endl;
    return 1;
  }
  string alvo = argv[1], nomePadrao = argv[3], saida = argv[4];
  int semente = atoi(argv[2]);
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  auto p = find_if(PADROES.begin(), PADROES.end(), [&](auto &q) { return q.nome == nomePadrao; });
  if (it == MAPAS.end() || p == PADROES.end()) {
    cerr << "mapa ou padrao desconhecido" << endl;
    return 1;
  }
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  protegeExtremos(scen);
  set<pair<int, int>> extremos;
  for (auto &q : scen) extremos.insert(q.start), extremos.insert(q.goal);
  auto original = grid;
  filesystem::create_directories(saida);
  string base = saida + "/" + alvo + "_" + to_string(semente) + "_" + nomePadrao;

  grid = degradaNiveis(p->v1, semente, false, original).back().grid;
  grava(base + "_v1_30.txt", original, extremos, false);
  grid = degradaNiveis(p->v2, semente, true, original).back().grid;
  grava(base + "_v2_30.txt", original, extremos, true);
  return 0;
}
