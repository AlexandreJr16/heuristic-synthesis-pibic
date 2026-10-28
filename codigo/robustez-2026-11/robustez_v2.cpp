// Robustez com o protocolo de degradacao v2 para um (mapa, semente). Reproduz o laco de
// main.cpp:147-266 trocando a degradacao e validando os pares em cada nivel (ver P2)
#include "degradacao_v2.h"
#include "../medicoes-2026-08/checkpoint.h"
#include <sys/resource.h>

struct PerfData { int exp; double time; int path; };

static PerfData mede(const ScenProblem &p, function<int(pair<int, int>, pair<int, int>)> h) {
  auto t1 = chrono::high_resolution_clock::now();
  auto r = aStar(p.start, p.goal, h);
  auto t2 = chrono::high_resolution_clock::now();
  return {r.expansions, chrono::duration<double, milli>(t2 - t1).count(), (int)r.path.size() - 1};
}

static bool existe(const string &f) { return ifstream(f).good(); }

// Primeira linha do mapa em resultados_sintese.csv (arena aparece duas vezes, P7)
static string formulaDoMapa(const string &mapa) {
  ifstream f("../../dados/resultados_sintese.csv");
  string l;
  while (getline(f, l))
    if (l.rfind(mapa + ",", 0) == 0) {
      size_t a = l.find('"'), b = l.find('"', a + 1);
      return l.substr(a + 1, b - a - 1);
    }
  throw runtime_error("formula nao encontrada para " + mapa);
}

// Mesma amostra de aptidao de main.cpp:108-117
static vector<char> amostraTreino(int n) {
  vector<char> t(n, 0);
  int tam = min(n, max(150, n / 4));
  int estrato = n / tam;
  srand(42);
  for (int i = 0; i < tam; i++) {
    int ini = i * estrato, fim = min(n, (i + 1) * estrato);
    t[ini + rand() % (fim - ini)] = 1;
  }
  return t;
}

// Compara expansoes e caminho com resultados_base.csv de marco (1a ocorrencia, P7); aborta se divergir
static void confereMarco(const string &mapa, int semente, const vector<PerfData> &manh,
                         const vector<PerfData> &form, map<int, vector<PerfData>> &mem) {
  const char *d = getenv("HEURISTICAS_DADOS");
  string arq = string(d ? d : "../../dados/brutos") + "/resultados_base.csv";
  ifstream f(arq);
  if (!f.is_open()) {
    cerr << "nao achei " << arq << " (defina HEURISTICAS_DADOS)" << endl;
    exit(4);
  }
  string chave = mapa + "," + to_string(semente) + ",", l;
  map<tuple<int, string, int>, pair<int, int>> marco;
  while (getline(f, l)) {
    if (l.rfind(chave, 0) != 0) continue;
    stringstream ss(l.substr(chave.size()));
    string id, heur, n, exp, tempo, path;
    getline(ss, id, ',');
    getline(ss, heur, ',');
    getline(ss, n, ',');
    getline(ss, exp, ',');
    getline(ss, tempo, ',');
    getline(ss, path, ',');
    marco.insert({{stoi(id), heur, stoi(n)}, {stoi(exp), stoi(path)}});
  }
  int difs = 0;
  auto compara = [&](int i, const string &heur, int n, const PerfData &v) {
    auto it = marco.find({i, heur, n});
    if (it != marco.end() && it->second == make_pair(v.exp, v.path)) return;
    if (difs++ < 5)
      cerr << "  diverge: id=" << i << " " << heur << " n=" << n << " v2=" << v.exp << "/" << v.path
           << " marco=" << (it == marco.end() ? "ausente" : to_string(it->second.first) + "/" + to_string(it->second.second))
           << endl;
  };
  for (size_t i = 0; i < manh.size(); i++) {
    compara(i, "manhattan", 0, manh[i]);
    compara(i, "formula", 0, form[i]);
    for (int n : NUMPIVOS) compara(i, "memory", n, mem[n][i]);
  }
  if (difs || marco.size() != manh.size() * 6) {
    cerr << "LINHA DE BASE NAO BATE COM MARCO: " << difs << " divergencias, " << marco.size()
         << " linhas de marco para " << manh.size() * 6 << " esperadas" << endl;
    exit(4);
  }
  cerr << "  linha de base = marco (" << marco.size() << " linhas)" << endl;
}

int main(int argc, char **argv) {
  if (argc < 4) {
    cerr << "uso: robustez_v2 <mapa> <semente> <saida>" << endl;
    return 1;
  }
  string alvo = argv[1], saida = argv[3];
  int semente = atoi(argv[2]);
  filesystem::create_directories(saida + "/partes");
  string parte = saida + "/partes/" + alvo + "_" + to_string(semente);
  if (existe(parte + ".csv") && existe(parte + "_resumo.csv")) {
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
  currentFormula = parseFormula(formulaDoMapa(alvo));
  auto treino = amostraTreino(scen.size());

  srand(semente);
  vector<PerfData> baseManh(scen.size()), baseForm(scen.size());
  map<int, vector<PerfData>> baseMem;
  map<int, vector<pair<int, int>>> pivosPorN;
  map<int, vector<vector<vector<int>>>> distOriginal;
  for (size_t i = 0; i < scen.size(); i++) {
    baseManh[i] = mede(scen[i], heuristicaManhattan);
    baseForm[i] = mede(scen[i], heuristicaFormula);
  }
  for (int n : NUMPIVOS) {
    computarDistPivos(n);
    pivosPorN[n] = pivos;
    distOriginal[n] = distPivos;
    for (auto &p : scen) baseMem[n].push_back(mede(p, heuristicaMemoryBased));
  }
  confereMarco(alvo, semente, baseManh, baseForm, baseMem);

  auto original = grid;
  vector<int> tam;
  auto compOriginal = rotulaComponentes(tam);
  auto paresOriginal = paresConectados(scen);
  vector<int> comCaminho;
  for (size_t i = 0; i < scen.size(); i++)
    if (baseManh[i].path >= 0) comCaminho.push_back(i);
  if (comCaminho != paresOriginal) {
    cerr << "pares com caminho no A* != pares na mesma componente" << endl;
    return 5;
  }
  protegeExtremos(scen);

  ofstream csv(parte + ".csv.tmp", ios::trunc), res(parte + "_resumo.csv.tmp", ios::trunc);
  csv << "mapa,semente,id_problema,tipo_degradacao,n_pivos,porcentagem_bloqueio,"
         "exp_orig_manh,exp_deg_manh,exp_orig_form,exp_deg_form,exp_orig_mem,exp_deg_mem,"
         "path_orig_manh,path_deg_manh,path_orig_form,path_deg_form,path_orig_mem,path_deg_mem,"
         "tempo_orig_manh_ms,tempo_deg_manh_ms,tempo_orig_form_ms,tempo_deg_form_ms,tempo_orig_mem_ms,tempo_deg_mem_ms,"
         "exp_deg_mem_congelado,em_treino\n";
  res << "mapa,semente,padrao,nivel,pct_atingido,rejeitadas_r1,rejeitadas_r2,pares_validos,"
         "pares_validos_v1,pct_atingido_v1,colapso_pivo,pivos_colapsados\n";

  for (auto &p : PADROES) {
    auto td = chrono::high_resolution_clock::now();
    auto v1 = degradaNiveis(p.v1, semente, false, original);
    chamadasBfs = celulasBfs = 0;
    auto v2 = degradaNiveis(p.v2, semente, true, original);
    double msDeg = chrono::duration<double, milli>(chrono::high_resolution_clock::now() - td).count();
    cerr << "  " << p.nome << ": degradacao v1+v2 " << (long)msDeg << " ms, bfs " << chamadasBfs
         << " chamadas / " << celulasBfs << " celulas" << endl;

    for (size_t k = 0; k < NIVEIS.size(); k++) {
      double pct = NIVEIS[k];
      grid = v1[k].grid;
      int validosV1 = paresConectados(scen).size();
      grid = v2[k].grid;
      auto validos = verificaNivel(k ? v2[k - 1].grid : original, compOriginal, tam.size(), scen, paresOriginal,
                                   alvo + " s" + to_string(semente) + " " + p.nome + " " + to_string(pct));

      vector<PerfData> degManh(scen.size()), degForm(scen.size());
      for (int i : validos) {
        degManh[i] = mede(scen[i], heuristicaManhattan);
        degForm[i] = mede(scen[i], heuristicaFormula);
        if (degManh[i].path < 0 || degForm[i].path < 0) {
          cerr << "par valido sem caminho: id=" << i << endl;
          return 5;
        }
      }
      string colapsados;
      for (int n : NUMPIVOS) {
        computarDistPivosFixos(pivosPorN[n]);
        int zeros = 0;
        for (int i : validos) zeros += heuristicaMemoryBased(scen[i].start, scen[i].goal) == 0;
        if (zeros > 0.5 * validos.size()) colapsados += (colapsados.empty() ? "" : ";") + to_string(n);
        vector<PerfData> degMem(scen.size());
        for (int i : validos) degMem[i] = mede(scen[i], heuristicaMemoryBased);
        swap(distPivos, distOriginal[n]);
        vector<int> congelado(scen.size());
        for (int i : validos) congelado[i] = aStar(scen[i].start, scen[i].goal, heuristicaMemoryBased).expansions;
        swap(distPivos, distOriginal[n]);
        for (int i : validos)
          csv << alvo << "," << semente << "," << i << "," << p.nome << "," << n << "," << pct << ","
              << baseManh[i].exp << "," << degManh[i].exp << "," << baseForm[i].exp << "," << degForm[i].exp << ","
              << baseMem[n][i].exp << "," << degMem[i].exp << "," << baseManh[i].path << "," << degManh[i].path << ","
              << baseForm[i].path << "," << degForm[i].path << "," << baseMem[n][i].path << "," << degMem[i].path << ","
              << baseManh[i].time << "," << degManh[i].time << "," << baseForm[i].time << "," << degForm[i].time << ","
              << baseMem[n][i].time << "," << degMem[i].time << "," << congelado[i] << "," << (int)treino[i] << "\n";
      }
      res << alvo << "," << semente << "," << p.nome << "," << pct << "," << fixed << setprecision(6) << v2[k].pct
          << "," << v2[k].r1 << "," << v2[k].r2 << "," << validos.size() << "," << validosV1 << "," << v1[k].pct
          << "," << (colapsados.empty() ? "nao" : "sim") << "," << (colapsados.empty() ? "-" : colapsados) << "\n"
          << defaultfloat;
      cerr << "    " << pct << ": bloqueio " << v2[k].pct << " (v1 " << v1[k].pct << "), pares " << validos.size()
           << " (v1 " << validosV1 << "), rejeitadas r1=" << v2[k].r1 << " r2=" << v2[k].r2
           << (colapsados.empty() ? "" : ", colapso n=" + colapsados) << endl;
    }
  }
  csv.close();
  res.close();
  if (!csv || !res) {
    cerr << "falha ao gravar " << parte << endl;
    return 6;
  }
  rename((parte + ".csv.tmp").c_str(), (parte + ".csv").c_str());
  rename((parte + "_resumo.csv.tmp").c_str(), (parte + "_resumo.csv").c_str());
  struct rusage ru;
  getrusage(RUSAGE_SELF, &ru);
  cerr << "[" << alvo << " s" << semente << " pronto em "
       << chrono::duration<double>(chrono::high_resolution_clock::now() - t0).count() << " s, pico "
       << ru.ru_maxrss / 1024 << " MB]" << endl;
  return 0;
}
