// Testes do gerador v2 em cada mapa pedido, 5 sementes x 5 padroes:
// fidelidade a map.cpp com as regras desligadas, R1, R2, cumulatividade e determinismo
#include "degradacao_v2.h"
#include <sys/wait.h>

static vector<uint64_t> hashes(const vector<Nivel> &niveis) {
  vector<uint64_t> h;
  for (auto &n : niveis) {
    grid = n.grid;
    h.push_back(hashGrid());
  }
  return h;
}

// Controle negativo: verificaNivel tem que abortar (exit 5) com o grid v1 do Linear a 10%;
// roda num processo filho porque a verificacao encerra o processo
static bool reprovaV1(const vector<vector<bool>> &original, const vector<vector<int>> &compOriginal,
                      int nComp, const vector<ScenProblem> &scen, const vector<int> &paresOriginal) {
  auto v1 = degradaNiveis(PADROES[1].v1, SEMENTES[0], false, original);
  pid_t pid = fork();
  if (pid == 0) {
    freopen("/dev/null", "w", stderr);
    grid = v1[0].grid;
    verificaNivel(original, compOriginal, nComp, scen, paresOriginal, "controle negativo");
    _exit(0);
  }
  int st = 0;
  waitpid(pid, &st, 0);
  return WIFEXITED(st) && WEXITSTATUS(st) == 5;
}

int main(int argc, char **argv) {
  vector<string> alvos;
  for (int i = 1; i < argc; i++) alvos.push_back(argv[i]);
  if (alvos.empty()) alvos = {"arena", "brc201d"};
  int falhas = 0;
  for (auto &alvo : alvos) {
    auto it = find_if(MAPAS.begin(), MAPAS.end(), [&](auto &m) { return m.first == alvo; });
    if (it == MAPAS.end()) {
      cerr << "mapa desconhecido: " << alvo << endl;
      return 1;
    }
    loadMap(it->second + ".map");
    auto scen = loadScenario(it->second + ".map.scen");
    auto original = grid;
    vector<int> tam;
    auto compOriginal = rotulaComponentes(tam);
    auto paresOriginal = paresConectados(scen);
    protegeExtremos(scen);
    cout << alvo << ": |S|=" << originalTraversableCells << " componentes=" << tam.size()
         << " pares=" << scen.size() << " conectados=" << paresOriginal.size() << endl;

    bool reprova = reprovaV1(original, compOriginal, tam.size(), scen, paresOriginal);
    falhas += !reprova;
    cout << "  controle negativo (grid v1, Linear s" << SEMENTES[0] << " 10%): "
         << (reprova ? "reprovado, ok" : "NAO REPROVOU") << endl;

    for (int semente : SEMENTES)
      for (auto &p : PADROES) {
        string ctx = alvo + " s" + to_string(semente) + " " + p.nome;
        aplicaRegras = false;
        bool fiel = hashes(degradaNiveis(p.v2, semente, false, original)) ==
                    hashes(degradaNiveis(p.v1, semente, false, original));
        aplicaRegras = true;
        auto a = degradaNiveis(p.v2, semente, true, original);
        auto b = degradaNiveis(p.v2, semente, true, original);
        bool determinista = hashes(a) == hashes(b);
        int maxComp = 0;
        for (size_t k = 0; k < a.size(); k++) {
          grid = a[k].grid;
          verificaNivel(k ? a[k - 1].grid : original, compOriginal, tam.size(), scen, paresOriginal,
                        ctx + " " + to_string(NIVEIS[k]));
          vector<int> t;
          rotulaComponentes(t);
          maxComp = max(maxComp, (int)t.size());
        }
        falhas += !fiel + !determinista;
        cout << "  " << ctx << ": fidelidade=" << (fiel ? "ok" : "FALHOU")
             << " determinismo=" << (determinista ? "ok" : "FALHOU") << " R1/R2/cumulativa=ok"
             << " componentes<=" << maxComp << " pct=" << fixed << setprecision(4) << a[0].pct << "/"
             << a[1].pct << "/" << a[2].pct << " rejeitadas_r1=" << a[2].r1 << " r2=" << a[2].r2
             << " tentativas=" << a[2].t1 << "/" << a[2].t2 << endl;
      }
  }
  cout << (falhas ? "FALHOU" : "PASSOU") << " (" << falhas << " falhas)" << endl;
  return falhas ? 1 : 0;
}
