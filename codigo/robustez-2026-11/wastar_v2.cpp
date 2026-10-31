// Controle da formula contra o Weighted A* (h = floor(w * Manhattan)) com qualidade de caminho casada.
// Usa o aStar de marco sem mudanca (mesma fila, mesmo desempate pelo g, sem reabrir fechados).
// O floor mantem h <= w * h*, entao o custo continua <= w * otimo, e com w = 1 o h e o da Manhattan.
// O teto do WA* (w -> infinito) e a busca gulosa (GBFS, f = h): uma copia do aStar que so troca a prioridade.
// Nos arquivos, w = inf e a GBFS.
//
//   wastar_v2 calibra <mapa> <saida>          uma vez por mapa (o original nao depende da semente)
//     _w1.csv          w = 1 em todos os pares conectados do original e nos 5 padroes a 30% da semente 42
//     _calibracao.csv  cada peso testado (grade, ampliacao, GBFS, bissecao) e a formula, em treino e fora do treino
//     _pesos.csv       categoria, rho alvo, w_inf, w_estrela, w_sup e como a bissecao terminou
//     _orig.csv        w_inf, w_estrela, w_sup e GBFS por par fora do treino, no original
//   wastar_v2 avalia <mapa> <semente> <saida>  os mesmos pesos nos pares validos fora do treino, 5 padroes x 3 niveis
//     _<semente>_aval.csv
//
// Categorias da calibracao:
//   casado         rho alvo cercado por dois pesos finitos (grade, ampliacao ate 10, bissecao)
//   casado_gbfs    so a GBFS passa do rho alvo: w_sup = GBFS, bissecao em 1/w entre o maior w finito e 0
//   fora_da_curva  nem a GBFS chega ao rho alvo: sem w_estrela nem w_sup; w_inf = maior w finito
#include "degradacao_v2.h"
#include "../medicoes-2026-08/checkpoint.h"

static const vector<double> GRADE = {1.1, 1.25, 1.5, 2, 3};
static const vector<double> AMPLIACAO = {5, 10};
static const double TOLERANCIA = 0.005;
static const int MAX_ITERACOES = 8;
static const int SEMENTE_CONFERENCIA = 42;

// Copia de aStar (medicoes-2026-08/src/astar.cpp) com prioridade f = h no lugar de g + h. O resto e igual:
// mesmo comparador (empate em f -> maior g primeiro), sem reabrir fechados, mesma reconstrucao
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

static SearchResult busca(const ScenProblem &p, double w) {
  if (isinf(w)) return gbfs(p.start, p.goal);
  return aStar(p.start, p.goal,
               [w](pair<int, int> s, pair<int, int> g) { return (int)floor(w * heuristicaManhattan(s, g)); });
}

static double geom(const vector<double> &x) {
  double s = 0;
  for (double v : x) s += log(v);
  return x.empty() ? NAN : exp(s / x.size());
}

// rho de um caminho contra o otimo; origem = destino conta como rho = 1 (como no b2)
static double rho(int caminho, int otimo) { return otimo == 0 ? 1.0 : (double)caminho / otimo; }

struct Medida { int pares; double rho, exp, fracOtimos; };

static Medida resume(const vector<int> &ids, const vector<SearchResult> &r, const vector<int> &otimo) {
  vector<double> rh, ex;
  int otimos = 0;
  for (int i : ids) {
    int c = (int)r[i].path.size() - 1;
    rh.push_back(rho(c, otimo[i]));
    ex.push_back(max(1, r[i].expansions));
    otimos += c == otimo[i];
  }
  return {(int)ids.size(), geom(rh), geom(ex), ids.empty() ? NAN : (double)otimos / ids.size()};
}

static string arquivoBase(const string &saida, const string &mapa) { return saida + "/wastar/" + mapa; }

static bool grava(ofstream &f, const string &tmp, const string &final) {
  f.close();
  if (!f) return false;
  filesystem::rename(tmp, final);
  return true;
}

static int calibra(const string &alvo, const string &saida) {
  string base = arquivoBase(saida, alvo);
  vector<string> sufixos = {"_w1.csv", "_calibracao.csv", "_pesos.csv", "_orig.csv"};
  if (all_of(sufixos.begin(), sufixos.end(), [&](auto &s) { return filesystem::exists(base + s); })) {
    cerr << "[" << alvo << " ja calibrado, pulando]" << endl;
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
  currentFormula = parseFormula(formulaDoMapa(alvo));
  auto treino = amostraTreino(scen.size());
  auto conectados = paresConectados(scen);
  vector<int> idsTreino, idsTeste;
  for (int i : conectados) (treino[i] ? idsTreino : idsTeste).push_back(i);

  ofstream w1(base + "_w1.csv.tmp", ios::trunc), cal(base + "_calibracao.csv.tmp", ios::trunc),
      pes(base + "_pesos.csv.tmp", ios::trunc), ori(base + "_orig.csv.tmp", ios::trunc);
  w1 << "mapa,semente,id_problema,tipo_degradacao,porcentagem_bloqueio,exp_w1,path_w1\n";
  cal << "mapa,w,papel,iteracao,conjunto,pares,rho,exp_geom,frac_otimos\n";
  pes << "mapa,categoria,rho_alvo,exp_formula,w_inf,w_estrela,w_sup,rho_inf,rho_estrela,rho_sup,exp_inf,"
         "exp_estrela,exp_sup,rho_gbfs,exp_gbfs,iteracoes,grade_ampliada,atingiu_tolerancia\n";
  ori << "mapa,id_problema,papel,w,exp,path\n";
  cal << setprecision(17);
  pes << setprecision(17);
  ori << setprecision(17);

  // w = 1 no original: e o otimo de referencia e a primeira conferencia
  vector<SearchResult> r1(scen.size());
  vector<int> otimo(scen.size(), -1);
  for (int i : conectados) {
    r1[i] = busca(scen[i], 1.0);
    otimo[i] = (int)r1[i].path.size() - 1;
    w1 << alvo << ",-1," << i << ",original,0," << r1[i].expansions << "," << otimo[i] << "\n";
  }

  // cada peso testado, nos dois conjuntos
  map<double, pair<Medida, Medida>> medido;
  auto mede = [&](double w, const string &papel, int iteracao) {
    if (!medido.count(w)) {
      vector<SearchResult> r(scen.size());
      for (int i : conectados) r[i] = busca(scen[i], w);
      medido[w] = {resume(idsTreino, r, otimo), resume(idsTeste, r, otimo)};
    }
    auto &[mt, mv] = medido[w];
    for (auto &[nome, m] : vector<pair<string, Medida>>{{"treino", mt}, {"teste", mv}})
      cal << alvo << "," << w << "," << papel << "," << iteracao << "," << nome << "," << m.pares << "," << m.rho
          << "," << m.exp << "," << m.fracOtimos << "\n";
    return mt.rho;
  };

  // formula, para o alvo e para as curvas
  vector<SearchResult> rf(scen.size());
  for (int i : conectados) rf[i] = aStar(scen[i].start, scen[i].goal, heuristicaFormula);
  Medida ft = resume(idsTreino, rf, otimo), fv = resume(idsTeste, rf, otimo);
  for (auto &[nome, m] : vector<pair<string, Medida>>{{"treino", ft}, {"teste", fv}})
    cal << alvo << ",," << "formula,0," << nome << "," << m.pares << "," << m.rho << "," << m.exp << ","
        << m.fracOtimos << "\n";
  double rhoAlvo = ft.rho;
  vector<pair<double, double>> pontos = {{1.0, mede(1.0, "manhattan", 0)}};
  for (double w : GRADE) pontos.push_back({w, mede(w, "grade", 0)});

  // primeiro par de vizinhos com rho(w_a) <= alvo <= rho(w_b)
  auto cerco = [&]() {
    for (size_t k = 0; k + 1 < pontos.size(); k++)
      if (pontos[k].second <= rhoAlvo && rhoAlvo <= pontos[k + 1].second) return (int)k;
    return -1;
  };
  bool ampliada = false;
  int k = cerco();
  if (k < 0 && rhoAlvo > pontos.back().second) {
    ampliada = true;
    for (double w : AMPLIACAO) pontos.push_back({w, mede(w, "ampliada", 0)});
    k = cerco();
  }
  double rhoG = mede(INFINITY, "gbfs", 0);
  string categoria = "casado";
  if (k < 0 && rhoAlvo > pontos.back().second) {
    pontos.push_back({INFINITY, rhoG});
    k = cerco();
    categoria = k < 0 ? "fora_da_curva" : "casado_gbfs";
  }
  if (k < 0 && categoria != "fora_da_curva") {
    cerr << alvo << ": rho alvo " << rhoAlvo << " abaixo da curva do WA* sem cerco (rho nao monotono)" << endl;
    return 7;
  }

  double lo = NAN, hi = NAN, rlo = NAN, rhi = NAN, estrela = NAN;
  int iteracoes = 0;
  if (categoria == "fora_da_curva") {
    lo = AMPLIACAO.back();
    rlo = medido[lo].first.rho;
  } else {
    lo = pontos[k].first, hi = pontos[k + 1].first, rlo = pontos[k].second, rhi = pontos[k + 1].second;
    for (int itb = 1; itb <= MAX_ITERACOES; itb++) {
      iteracoes = itb;
      // com w_sup = GBFS a bissecao e em 1/w (meio de 1/lo e 0 = 2 lo)
      double meio = isinf(hi) ? 2 * lo : (lo + hi) / 2, rm = mede(meio, "bissecao", itb);
      if (fabs(rm - rhoAlvo) <= TOLERANCIA) {
        estrela = meio;
        break;
      }
      if (rm <= rhoAlvo) lo = meio, rlo = rm;
      else hi = meio, rhi = rm;
    }
    if (isnan(estrela)) {
      double melhor = INFINITY;
      for (auto &[w, m] : medido)
        if (fabs(m.first.rho - rhoAlvo) < melhor) melhor = fabs(m.first.rho - rhoAlvo), estrela = w;
    }
  }
  bool atingiu = categoria != "fora_da_curva" && fabs(medido[estrela].first.rho - rhoAlvo) <= TOLERANCIA;
  auto campo = [&](double w, bool rhoNaoExp) {
    if (isnan(w)) return string("nan");
    ostringstream o;
    o << setprecision(17) << (rhoNaoExp ? medido[w].first.rho : medido[w].first.exp);
    return o.str();
  };
  pes << alvo << "," << categoria << "," << rhoAlvo << "," << ft.exp << "," << lo << "," << estrela << "," << hi
      << "," << rlo << "," << campo(estrela, true) << "," << rhi << "," << campo(lo, false) << ","
      << campo(estrela, false) << "," << campo(hi, false) << "," << rhoG << "," << medido[INFINITY].first.exp << ","
      << iteracoes << "," << ampliada << "," << atingiu << "\n";

  vector<pair<string, double>> papeis = {{"w_inf", lo}, {"w_estrela", estrela}, {"w_sup", hi}, {"gbfs", INFINITY}};
  for (auto &[papel, w] : papeis) {
    if (isnan(w)) continue;
    for (int i : idsTeste) {
      auto r = busca(scen[i], w);
      ori << alvo << "," << i << "," << papel << "," << w << "," << r.expansions << "," << (int)r.path.size() - 1
          << "\n";
    }
  }

  // w = 1 nos 5 padroes a 30% da semente de conferencia
  auto original = grid;
  vector<int> tam;
  auto compOriginal = rotulaComponentes(tam);
  protegeExtremos(scen);
  for (auto &p : PADROES) {
    auto v2 = degradaNiveis(p.v2, SEMENTE_CONFERENCIA, true, original);
    size_t n = NIVEIS.size() - 1;
    grid = v2[n].grid;
    auto validos = verificaNivel(v2[n - 1].grid, compOriginal, tam.size(), scen, conectados,
                                 alvo + " s" + to_string(SEMENTE_CONFERENCIA) + " " + p.nome);
    for (int i : validos) {
      auto r = busca(scen[i], 1.0);
      w1 << alvo << "," << SEMENTE_CONFERENCIA << "," << i << "," << p.nome << "," << NIVEIS[n] << ","
         << r.expansions << "," << (int)r.path.size() - 1 << "\n";
    }
  }
  grid = original;

  bool ok = grava(w1, base + "_w1.csv.tmp", base + "_w1.csv");
  ok = grava(cal, base + "_calibracao.csv.tmp", base + "_calibracao.csv") && ok;
  ok = grava(ori, base + "_orig.csv.tmp", base + "_orig.csv") && ok;
  ok = grava(pes, base + "_pesos.csv.tmp", base + "_pesos.csv") && ok;
  if (!ok) {
    cerr << "falha ao gravar " << base << endl;
    return 6;
  }
  cerr << "[" << alvo << " " << categoria << ": rho alvo " << rhoAlvo << ", w* " << estrela << " em [" << lo << ", "
       << hi << "], rho GBFS " << rhoG << ", " << iteracoes << " iteracoes" << (ampliada ? ", grade ampliada" : "")
       << (atingiu ? "" : ", sem tolerancia") << ", "
       << chrono::duration<double>(chrono::high_resolution_clock::now() - t0).count() << " s]" << endl;
  return 0;
}

static int avalia(const string &alvo, int semente, const string &saida) {
  string base = arquivoBase(saida, alvo), arq = base + "_" + to_string(semente) + "_aval.csv";
  if (filesystem::exists(arq)) {
    cerr << "[" << alvo << " s" << semente << " ja avaliado, pulando]" << endl;
    return 0;
  }
  auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
  if (it == MAPAS.end()) {
    cerr << "mapa desconhecido: " << alvo << endl;
    return 1;
  }
  ifstream fp(base + "_pesos.csv");
  string cab, l;
  getline(fp, cab);
  if (!getline(fp, l)) {
    cerr << "sem calibracao para " << alvo << " (rode wastar_v2 calibra)" << endl;
    return 1;
  }
  map<string, string> c;
  stringstream sc(cab), sl(l);
  for (string a, b; getline(sc, a, ',') && getline(sl, b, ',');) c[a] = b;
  vector<pair<string, double>> pesos;
  for (string p : {"w_inf", "w_estrela", "w_sup"})
    if (!isnan(stod(c[p]))) pesos.push_back({p, stod(c[p])});
  pesos.push_back({"gbfs", INFINITY});

  auto t0 = chrono::high_resolution_clock::now();
  loadMap(it->second + ".map");
  auto scen = loadScenario(it->second + ".map.scen");
  auto treino = amostraTreino(scen.size());
  auto original = grid;
  vector<int> tam;
  auto compOriginal = rotulaComponentes(tam);
  auto paresOriginal = paresConectados(scen);
  protegeExtremos(scen);

  ofstream av(arq + ".tmp", ios::trunc);
  av << "mapa,semente,id_problema,tipo_degradacao,porcentagem_bloqueio,papel,w,exp,path\n" << setprecision(17);
  for (auto &p : PADROES) {
    auto v2 = degradaNiveis(p.v2, semente, true, original);
    for (size_t k = 0; k < NIVEIS.size(); k++) {
      grid = v2[k].grid;
      auto validos = verificaNivel(k ? v2[k - 1].grid : original, compOriginal, tam.size(), scen, paresOriginal,
                                   alvo + " s" + to_string(semente) + " " + p.nome + " " + to_string(NIVEIS[k]));
      for (auto &[papel, w] : pesos)
        for (int i : validos) {
          if (treino[i]) continue;
          auto r = busca(scen[i], w);
          if (r.path.empty()) {
            cerr << "par valido sem caminho: id=" << i << endl;
            return 5;
          }
          av << alvo << "," << semente << "," << i << "," << p.nome << "," << NIVEIS[k] << "," << papel << "," << w
             << "," << r.expansions << "," << (int)r.path.size() - 1 << "\n";
        }
    }
  }
  if (!grava(av, arq + ".tmp", arq)) {
    cerr << "falha ao gravar " << arq << endl;
    return 6;
  }
  cerr << "[" << alvo << " s" << semente << " avaliado em "
       << chrono::duration<double>(chrono::high_resolution_clock::now() - t0).count() << " s]" << endl;
  return 0;
}

int main(int argc, char **argv) {
  string modo = argc > 1 ? argv[1] : "";
  if (modo == "calibra" && argc >= 4) {
    filesystem::create_directories(string(argv[3]) + "/wastar");
    return calibra(argv[2], argv[3]);
  }
  if (modo == "avalia" && argc >= 5) {
    filesystem::create_directories(string(argv[4]) + "/wastar");
    return avalia(argv[2], atoi(argv[3]), argv[4]);
  }
  cerr << "uso: wastar_v2 calibra <mapa> <saida> | wastar_v2 avalia <mapa> <semente> <saida>" << endl;
  return 1;
}
