// Teste 2 do JBCS: tempo de relogio por busca e por visita da BFS, para medir o c (custo de uma expansao do A*
// em visitas da BFS) no lugar de assumi-lo. Um mapa por invocacao, uma thread; rode sem outro processo do
// experimento ao mesmo tempo e preso a um nucleo (taskset).
//
// Pares: ate 200 pares fora do treino do AG (amostraTreino == 0), estratificados pelo comprimento otimo no
// original (caminho da Manhattan): ordena, divide em 200 estratos de tamanho igual e sorteia um par por estrato
// com mt19937(20260820). Os mesmos pares no original e no degradado (Organic, 30%, semente 42, v2).
// Heuristicas: Manhattan, Memoria-10/20/50/100 (atualizada no degradado; tambem a congelada, para o regime sem
// atualizacao), formula de marco, WA* com w* (w_inf quando o mapa e fora da curva) e GBFS.
// Protocolo: por par e heuristica, 1 execucao de aquecimento e 5 medicoes com steady_clock so em volta da busca.
// BFS: por numero de pivos, o recalculo completo (computarDistPivosFixos) no degradado, 1 aquecimento e 5 medicoes.
//
//   ./tempo_v2 <mapa> <saida>  ->  <saida>/tempo/<mapa>_busca.csv e <mapa>_bfs.csv
#include "degradacao_v2.h"
#include "../medicoes-2026-08/checkpoint.h"

static const int REPETICOES = 5, PARES = 200;
static const unsigned SEMENTE_AMOSTRA = 20260820;

// Copia da gbfs de wastar_v2.cpp (f = h, empate -> maior g, sem reabrir fechados)
static SearchResult gbfs(pair<int, int> start, pair<int, int> goal) {
  SearchResult res;
  res.expansions = 0;
  priority_queue<pair<int, tipoNo>, vector<pair<int, tipoNo>>, comparadorTipoNo> aberta;
  vector<vector<bool>> fechado(height, vector<bool>(width, false));
  vector<vector<pair<int, int>>> pai(height, vector<pair<int, int>>(width, {-1, -1}));
  vector<vector<int>> melhorG(height, vector<int>(width, INT_MAX));
  tipoNo inicio, vizinho;
  inicio.coord = start;
  inicio.pai = {-1, -1};
  inicio.g = 0;
  melhorG[start.first][start.second] = 0;
  aberta.push({heuristicaManhattan(start, goal), inicio});
  while (!aberta.empty()) {
    auto [f, atual] = aberta.top();
    aberta.pop();
    if (atual.g != melhorG[atual.coord.first][atual.coord.second]) continue;
    fechado[atual.coord.first][atual.coord.second] = true;
    res.expansions++;
    if (atual.coord == goal) {
      for (auto aux = goal; aux != start; aux = pai[aux.first][aux.second]) res.path.push_back(aux);
      res.path.push_back(start);
      reverse(res.path.begin(), res.path.end());
      return res;
    }
    for (int i = 0; i < 4; i++) {
      int x = atual.coord.first + px[i], y = atual.coord.second + py[i];
      if (x < 0 || x >= height || y < 0 || y >= width || !grid[x][y] || fechado[x][y]) continue;
      int novoG = atual.g + 1;
      if (novoG < melhorG[x][y]) {
        melhorG[x][y] = novoG;
        pai[x][y] = atual.coord;
        vizinho.coord = {x, y};
        vizinho.pai = atual.coord;
        vizinho.g = novoG;
        aberta.push({heuristicaManhattan({x, y}, goal), vizinho});
      }
    }
  }
  return res;
}

static double pesoWastar(const string &arq, const string &mapa, string &origem) {
  ifstream f(arq);
  string l, cab;
  getline(f, cab);
  while (getline(f, l)) {
    if (l.rfind(mapa + ",", 0) != 0) continue;
    vector<string> c;
    stringstream ss(l);
    string x;
    while (getline(ss, x, ',')) c.push_back(x);
    // mapa,categoria,rho_alvo,exp_formula,w_inf,w_estrela,...
    if (c[5] != "nan") return origem = "w_estrela", stod(c[5]);
    return origem = "w_inf", stod(c[4]);
  }
  throw runtime_error("peso do WA* nao encontrado para " + mapa);
}

template <class F> static pair<double, SearchResult> cronometra(F &&busca) {
  auto r = busca();  // aquecimento
  vector<double> t;
  for (int k = 0; k < REPETICOES; k++) {
    auto t1 = chrono::steady_clock::now();
    r = busca();
    auto t2 = chrono::steady_clock::now();
    t.push_back(chrono::duration<double, nano>(t2 - t1).count());
  }
  sort(t.begin(), t.end());
  return {t[REPETICOES / 2], r};
}

int main(int argc, char **argv) {
  if (argc < 3) {
    cerr << "uso: tempo_v2 <mapa> <saida>" << endl;
    return 1;
  }
  string alvo = argv[1], saida = argv[2];
  filesystem::create_directories(saida + "/tempo");
  string base = saida + "/tempo/" + alvo;
  if (filesystem::exists(base + "_busca.csv") && filesystem::exists(base + "_bfs.csv")) {
    cerr << "[" << alvo << " ja medido, pulando]" << endl;
    return 0;
  }
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  if (it == MAPAS.end()) {
    cerr << "mapa desconhecido: " << alvo << endl;
    return 1;
  }
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  currentFormula = parseFormula(formulaDoMapa(alvo));
  auto treino = amostraTreino(scen.size());
  string origemW;
  double w = pesoWastar(saida + "/wastar_pesos.csv", alvo, origemW);
  auto original = grid;
  vector<int> tam;
  auto compOriginal = rotulaComponentes(tam);
  auto paresOriginal = paresConectados(scen);

  // amostra estratificada pelo comprimento otimo no original
  vector<pair<int, int>> cand;  // (comprimento, id)
  for (int i : paresOriginal)
    if (!treino[i]) cand.push_back({(int)aStar(scen[i].start, scen[i].goal, heuristicaManhattan).path.size() - 1, i});
  sort(cand.begin(), cand.end());
  mt19937 rng(SEMENTE_AMOSTRA);
  vector<int> amostra;
  int ne = min<int>(PARES, cand.size());
  for (int e = 0; e < ne; e++) {
    size_t a = (size_t)e * cand.size() / ne, b = (size_t)(e + 1) * cand.size() / ne;
    amostra.push_back(cand[a + uniform_int_distribution<size_t>(0, b - a - 1)(rng)].second);
  }
  cerr << alvo << ": " << cand.size() << " pares fora do treino, amostra " << amostra.size() << ", WA* " << origemW
       << " = " << w << endl;

  // pivos na ordem de robustez_v2 (srand(42), 10 -> 20 -> 50 -> 100)
  srand(42);
  map<int, vector<pair<int, int>>> pivosPorN;
  map<int, vector<vector<vector<int>>>> distOriginal, distAtual;
  for (int n : NUMPIVOS) {
    computarDistPivos(n);
    pivosPorN[n] = pivos;
    distOriginal[n] = distPivos;
  }
  protegeExtremos(scen);
  int iOrganic = -1;
  for (size_t p = 0; p < PADROES.size(); p++)
    if (PADROES[p].nome == "Organic") iOrganic = p;
  auto v2 = degradaNiveis(PADROES[iOrganic].v2, 42, true, original);
  auto degradado = v2[2].grid;

  ofstream busca(base + "_busca.csv.tmp", ios::trunc), bfs(base + "_bfs.csv.tmp", ios::trunc);
  busca << "mapa,estado,id_problema,comprimento_otimo,heuristica,exp,path,t_mediana_ns\n";
  bfs << "mapa,n_pivos,visitas,t_mediana_ns\n";
  map<int, int> comp;
  for (auto &[c, i] : cand) comp[i] = c;

  for (string estado : {"original", "degradado"}) {
    grid = estado == "original" ? original : degradado;
    if (estado == "degradado") {
      verificaNivel(v2[1].grid, compOriginal, tam.size(), scen, paresOriginal, alvo + " Organic 30%");
      grid = degradado;
      for (int n : NUMPIVOS) {
        auto [t, r] = cronometra([&]() {
          computarDistPivosFixos(pivosPorN[n]);
          return SearchResult{};
        });
        long long visitas = 0;
        for (auto &d : distPivos)
          for (auto &linha : d)
            for (int x : linha) visitas += x >= 0;
        distAtual[n] = distPivos;
        bfs << alvo << "," << n << "," << visitas << "," << t << "\n";
      }
    } else {
      distAtual = distOriginal;
    }
    for (int i : amostra) {
      auto &p = scen[i];
      auto grava = [&](const string &h, pair<double, SearchResult> m) {
        busca << alvo << "," << estado << "," << i << "," << comp[i] << "," << h << "," << m.second.expansions << ","
              << (int)m.second.path.size() - 1 << "," << m.first << "\n";
      };
      grava("manhattan", cronometra([&]() { return aStar(p.start, p.goal, heuristicaManhattan); }));
      grava("formula", cronometra([&]() { return aStar(p.start, p.goal, heuristicaFormula); }));
      grava("wastar", cronometra([&]() {
              return aStar(p.start, p.goal,
                           [w](pair<int, int> s, pair<int, int> g) { return (int)floor(w * heuristicaManhattan(s, g)); });
            }));
      grava("gbfs", cronometra([&]() { return gbfs(p.start, p.goal); }));
      for (int n : NUMPIVOS) {
        pivos = pivosPorN[n];
        swap(distPivos, distAtual[n]);
        grava("mem" + to_string(n), cronometra([&]() { return aStar(p.start, p.goal, heuristicaMemoryBased); }));
        swap(distPivos, distAtual[n]);
        if (estado == "degradado") {
          swap(distPivos, distOriginal[n]);
          grava("mem" + to_string(n) + "_congelada",
                cronometra([&]() { return aStar(p.start, p.goal, heuristicaMemoryBased); }));
          swap(distPivos, distOriginal[n]);
        }
      }
    }
  }
  busca.close();
  bfs.close();
  if (!busca || !bfs) {
    cerr << "falha ao gravar " << base << endl;
    return 6;
  }
  filesystem::rename(base + "_busca.csv.tmp", base + "_busca.csv");
  filesystem::rename(base + "_bfs.csv.tmp", base + "_bfs.csv");
  cerr << "[" << alvo << " pronto]" << endl;
  return 0;
}
