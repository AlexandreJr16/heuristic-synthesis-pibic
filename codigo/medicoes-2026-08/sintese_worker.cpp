// Uma síntese (mapa, semente) por invocação, retomável.
//
//   ./sintese_worker <mapa> <run_seed> [gerações_por_checkpoint] [--saida <pasta>]
//
// Saídas em ../medicoes/sintese/ (ou na pasta de --saida):
//   <mapa>__<semente>.csv    resultado final (existir = tarefa concluída)
//   <mapa>__<semente>.ckpt   estado parcial (some quando a tarefa termina)
//
// Parada limpa: SIGINT/SIGTERM terminam a geração corrente, gravam checkpoint e
// saem com código 130. Queda de energia: perde-se no máximo o intervalo desde o
// último checkpoint. Em ambos os casos, basta reinvocar para continuar de onde parou.
#include "comum.h"
#include "checkpoint.h"

static volatile sig_atomic_t pedidoParada = 0;
static void aoSinal(int) { pedidoParada = 1; }

int main(int argc, char **argv) {
  // --saida <pasta> e opcional e pode vir em qualquer posicao; sem ele, a pasta antiga
  std::string dir = "../medicoes/sintese/";
  std::vector<std::string> pos;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    if (a == "--saida" && i + 1 < argc) { dir = argv[++i]; if (dir.back() != '/') dir += '/'; }
    else pos.push_back(a);
  }
  if (pos.size() < 2) { std::cerr << "uso: sintese_worker <mapa> <run_seed> [ckpt_every] [--saida <pasta>]\n"; return 2; }
  const std::string alvo = pos[0];
  const int runSeed = std::atoi(pos[1].c_str());
  const int ckptEvery = pos.size() > 2 ? std::atoi(pos[2].c_str()) : 5;

  signal(SIGINT, aoSinal); signal(SIGTERM, aoSinal);

  const std::string base = dir + alvo + "__" + std::to_string(runSeed);
  const std::string fResultado = base + ".csv", fCkpt = base + ".ckpt";
  { std::ifstream j(fResultado); if (j.good()) { std::cerr << "[já concluída]\n"; return 0; } }

  std::string mapPath;
  for (auto &[nome, b] : MAPAS) if (nome == alvo) mapPath = b;
  if (mapPath.empty()) { std::cerr << "mapa desconhecido: " << alvo << "\n"; return 2; }

  loadMap(mapPath + ".map");
  auto scenario = loadScenario(mapPath + ".map.scen");
  if (scenario.empty()) { std::cerr << "cenário vazio\n"; return 2; }

  // Fixos, exatamente como no experimento original (main.cpp:103-104,111):
  // só a semente do AG varia entre rodadas.
  HeuristicGrammar grammar(42);
  GeneticOperators operators(grammar, 42);
  GeneticAlgorithm ga(grammar, operators, runSeed);

  // Conjunto de treino: determinístico (srand(42)), então é recomputado na
  // retomada em vez de ser guardado no checkpoint.
  std::vector<ScenProblem> treino;
  int nTreino = std::min((int)scenario.size(), std::max(150, (int)scenario.size() / 4));
  int estrato = scenario.size() / nTreino;
  srand(42);
  for (int i = 0; i < nTreino; i++) {
    int a = i * estrato, b = std::min((int)scenario.size(), (i + 1) * estrato);
    treino.push_back(scenario[a + (rand() % (b - a))]);
  }
  std::vector<int> manhTreino(treino.size());
  for (size_t i = 0; i < treino.size(); ++i)
    manhTreino[i] = std::max(1, aStar(treino[i].start, treino[i].goal, heuristicaManhattan).expansions);

  int g0 = 0; double msAcumulado = 0;
  Estado est;
  if (carregarEstado(fCkpt, est) && est.mapa == alvo && est.semente == runSeed) {
    std::vector<Individual> pop;
    for (auto &[fit, s] : est.populacao) {
      Individual ind(parseFormula(s)); ind.fitness = fit; pop.push_back(ind);
    }
    grammar.setRngState(est.rngGrammar);
    operators.setRngState(est.rngOperators);
    ga.setRngState(est.rngGA);
    ga.restore(est.popSize, pop);
    g0 = est.geracao; msAcumulado = est.msAcumulado;
    std::cerr << "[retomando " << alvo << " s" << runSeed << " da geração " << g0 << "/100]\n";
  } else {
    ga.initPopulation(80);
    std::cerr << "[iniciando " << alvo << " s" << runSeed << "]\n";
  }

  auto avaliar = [&](std::shared_ptr<HeuristicNode> f) {
    long long tm = 0, tf = 0;
    for (size_t i = 0; i < treino.size(); ++i) {
      auto h = [&](std::pair<int,int> s, std::pair<int,int> gg) {
        return (int)f->evaluate({s.first, s.second}, {gg.first, gg.second}); };
      tm += manhTreino[i];
      tf += std::max(1, aStar(treino[i].start, treino[i].goal, h).expansions);
    }
    return (double)tm / (double)tf;
  };

  auto gravarCkpt = [&](int g, double ms) {
    Estado e; e.mapa = alvo; e.semente = runSeed; e.geracao = g;
    e.popSize = 80; e.msAcumulado = ms;
    e.rngGrammar = grammar.rngState();
    e.rngOperators = operators.rngState();
    e.rngGA = ga.rngState();
    for (auto &ind : ga.getPopulation())
      e.populacao.push_back({ind.fitness, ind.formula->toString()});
    salvarEstado(fCkpt, e);
  };

  auto t0 = std::chrono::high_resolution_clock::now();
  auto decorrido = [&] {
    return msAcumulado + std::chrono::duration<double, std::milli>(
        std::chrono::high_resolution_clock::now() - t0).count(); };

  for (int g = g0; g < 100; g++) {
    ga.evolve(avaliar);
    if (pedidoParada) {
      gravarCkpt(g + 1, decorrido());
      std::cerr << "[parado em " << alvo << " s" << runSeed << " na geração "
                << g + 1 << "/100 — checkpoint gravado]\n";
      return 130;
    }
    if ((g + 1) % ckptEvery == 0 && g + 1 < 100) gravarCkpt(g + 1, decorrido());
  }

  auto best = ga.getBest();
  std::ostringstream linha;
  linha << alvo << "," << runSeed << ",80,100," << std::fixed << std::setprecision(3)
        << decorrido() << ",\"" << best->toString() << "\","
        << std::setprecision(6) << ga.getBestFitness() << ","
        << best->size() << "," << best->depth() << "\n";
  gravarAtomico(fResultado, linha.str());
  std::remove(fCkpt.c_str());
  std::cerr << "[concluída " << alvo << " s" << runSeed << " fitness="
            << ga.getBestFitness() << " size=" << best->size()
            << " (" << decorrido() / 1000 << " s)]\n";
  return 0;
}
