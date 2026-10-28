// Quantos pivos caem em celula bloqueada sob degradacao, para v1 e v2. Os pivos sao os de
// robustez_v2 (srand(semente) e computarDistPivos(n) para n em NUMPIVOS, no original). bfsPivo
// nao confere grid[pivo]: um pivo bloqueado vira fonte da BFS; sem vizinho livre, so ele tem dist
#include "degradacao_v2.h"

static int vizinhosLivres(pair<int, int> c) {
  int n = 0;
  for (int k = 0; k < 4; k++) {
    int x = c.first + px[k], y = c.second + py[k];
    n += x >= 0 && x < height && y >= 0 && y < width && grid[x][y];
  }
  return n;
}

int main(int argc, char **argv) {
  if (argc < 3) {
    cerr << "uso: conta_pivos <mapa> <semente>" << endl;
    return 1;
  }
  string alvo = argv[1];
  int semente = atoi(argv[2]);
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  if (it == MAPAS.end()) {
    cerr << "mapa desconhecido: " << alvo << endl;
    return 1;
  }
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  protegeExtremos(scen);
  auto original = grid;

  srand(semente);
  map<int, vector<pair<int, int>>> pivosPorN;
  for (int n : NUMPIVOS) {
    computarDistPivos(n);
    pivosPorN[n] = pivos;
  }

  for (auto &p : PADROES)
    for (int v = 1; v <= 2; v++) {
      auto niveis = degradaNiveis(v == 1 ? p.v1 : p.v2, semente, v == 2, original);
      for (size_t k = 0; k < niveis.size(); k++) {
        grid = niveis[k].grid;
        for (int n : NUMPIVOS) {
          set<pair<int, int>> distintos(pivosPorN[n].begin(), pivosPorN[n].end());
          int bloqueados = 0, isolados = 0;
          for (auto &c : pivosPorN[n])
            if (!grid[c.first][c.second]) {
              bloqueados++;
              isolados += vizinhosLivres(c) == 0;
            }
          cout << alvo << "," << semente << ",v" << v << "," << p.nome << "," << NIVEIS[k] << "," << n << ","
               << pivosPorN[n].size() << "," << distintos.size() << "," << bloqueados << "," << isolados << "\n";
        }
      }
    }
  return 0;
}
