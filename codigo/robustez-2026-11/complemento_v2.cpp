// Medicoes complementares da robustez v2 para um (mapa, semente), com a mesma degradacao e os mesmos
// pivos de robustez_v2:
//   _congelada.csv  expansoes e caminho do A* com a memoria sem atualizacao (distancias do original)
//   _custo.csv      celulas visitadas pelas BFS dos pivos fixos no mapa degradado (custo de atualizar)
//   _otimo.csv      distancia BFS no mapa degradado para os pares com id % 10 == 0 (confere o otimo)
#include "degradacao_v2.h"

// Celulas que bfsPivo visita a partir de c: a componente de c, ou, se c esta bloqueada, ela mesma mais as
// componentes distintas dos vizinhos livres (bfsPivo nao confere grid[pivo])
static long long alcance(pair<int, int> c, const vector<vector<int>> &comp, const vector<int> &tam) {
  if (grid[c.first][c.second]) return tam[comp[c.first][c.second]];
  set<int> vistas;
  for (int k = 0; k < 4; k++) {
    int x = c.first + px[k], y = c.second + py[k];
    if (x >= 0 && x < height && y >= 0 && y < width && grid[x][y]) vistas.insert(comp[x][y]);
  }
  long long n = 1;
  for (int v : vistas) n += tam[v];
  return n;
}

static long long contaBfsReal(const vector<pair<int, int>> &pivosFixos) {
  long long n = 0;
  for (auto &p : pivosFixos)
    for (auto &linha : bfsPivo(p))
      for (int d : linha) n += d >= 0;
  return n;
}

static int distBfs(pair<int, int> s, pair<int, int> g) {
  vector<int> dist(height * width, -1);
  queue<int> q;
  dist[s.first * width + s.second] = 0;
  q.push(s.first * width + s.second);
  while (!q.empty()) {
    int v = q.front();
    q.pop();
    if (v == g.first * width + g.second) return dist[v];
    int vx = v / width, vy = v % width;
    for (int k = 0; k < 4; k++) {
      int x = vx + px[k], y = vy + py[k];
      if (x < 0 || x >= height || y < 0 || y >= width || !grid[x][y] || dist[x * width + y] >= 0) continue;
      dist[x * width + y] = dist[v] + 1;
      q.push(x * width + y);
    }
  }
  return -1;
}

int main(int argc, char **argv) {
  if (argc < 4) {
    cerr << "uso: complemento_v2 <mapa> <semente> <saida>" << endl;
    return 1;
  }
  string alvo = argv[1], saida = argv[3];
  int semente = atoi(argv[2]);
  filesystem::create_directories(saida + "/complemento");
  string parte = saida + "/complemento/" + alvo + "_" + to_string(semente);
  if (filesystem::exists(parte + "_congelada.csv") && filesystem::exists(parte + "_custo.csv") &&
      filesystem::exists(parte + "_otimo.csv")) {
    cerr << "[" << alvo << " s" << semente << " ja medido, pulando]" << endl;
    return 0;
  }
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  if (it == MAPAS.end()) {
    cerr << "mapa desconhecido: " << alvo << endl;
    return 1;
  }
  auto t0 = chrono::high_resolution_clock::now();
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  auto original = grid;
  vector<int> tamOriginal;
  auto compOriginal = rotulaComponentes(tamOriginal);
  auto paresOriginal = paresConectados(scen);

  srand(semente);
  map<int, vector<pair<int, int>>> pivosPorN;
  map<int, vector<vector<vector<int>>>> distOriginal;
  map<int, long long> custoOriginal;
  for (int n : NUMPIVOS) {
    computarDistPivos(n);
    pivosPorN[n] = pivos;
    distOriginal[n] = distPivos;
    for (auto &p : pivos) custoOriginal[n] += alcance(p, compOriginal, tamOriginal);
  }
  protegeExtremos(scen);

  ofstream cong(parte + "_congelada.csv.tmp", ios::trunc), custo(parte + "_custo.csv.tmp", ios::trunc),
      otimo(parte + "_otimo.csv.tmp", ios::trunc);
  cong << "mapa,semente,id_problema,tipo_degradacao,n_pivos,porcentagem_bloqueio,exp_deg_mem_congelado,"
          "path_deg_mem_congelado\n";
  custo << "mapa,semente,padrao,nivel,n_pivos,celulas_bfs_atualizacao,celulas_bfs_original,pivos_bloqueados\n";
  otimo << "mapa,semente,id_problema,tipo_degradacao,porcentagem_bloqueio,dist_bfs\n";

  bool conferido = false;
  for (auto &p : PADROES) {
    auto v2 = degradaNiveis(p.v2, semente, true, original);
    for (size_t k = 0; k < NIVEIS.size(); k++) {
      double pct = NIVEIS[k];
      grid = v2[k].grid;
      auto validos = verificaNivel(k ? v2[k - 1].grid : original, compOriginal, tamOriginal.size(), scen,
                                   paresOriginal, alvo + " s" + to_string(semente) + " " + p.nome);
      vector<int> tam;
      auto comp = rotulaComponentes(tam);
      for (int n : NUMPIVOS) {
        long long c = 0;
        int bloqueados = 0;
        for (auto &q : pivosPorN[n]) {
          c += alcance(q, comp, tam);
          bloqueados += !grid[q.first][q.second];
        }
        if (!conferido && contaBfsReal(pivosPorN[n]) != c) {
          cerr << "contagem por componente != BFS real: n=" << n << " " << p.nome << " " << pct << endl;
          return 5;
        }
        custo << alvo << "," << semente << "," << p.nome << "," << pct << "," << n << "," << c << ","
              << custoOriginal[n] << "," << bloqueados << "\n";
      }
      conferido = true;
      for (int i : validos)
        if (i % 10 == 0)
          otimo << alvo << "," << semente << "," << i << "," << p.nome << "," << pct << ","
                << distBfs(scen[i].start, scen[i].goal) << "\n";
      for (int n : NUMPIVOS) {
        pivos = pivosPorN[n];
        swap(distPivos, distOriginal[n]);
        for (int i : validos) {
          auto r = aStar(scen[i].start, scen[i].goal, heuristicaMemoryBased);
          cong << alvo << "," << semente << "," << i << "," << p.nome << "," << n << "," << pct << ","
               << r.expansions << "," << (int)r.path.size() - 1 << "\n";
        }
        swap(distPivos, distOriginal[n]);
      }
    }
  }
  cong.close();
  custo.close();
  otimo.close();
  if (!cong || !custo || !otimo) {
    cerr << "falha ao gravar " << parte << endl;
    return 6;
  }
  for (string s : {"_congelada.csv", "_custo.csv", "_otimo.csv"})
    filesystem::rename(parte + s + ".tmp", parte + s);
  cerr << "[" << alvo << " s" << semente << " pronto em "
       << chrono::duration<double>(chrono::high_resolution_clock::now() - t0).count() << " s]" << endl;
  return 0;
}
