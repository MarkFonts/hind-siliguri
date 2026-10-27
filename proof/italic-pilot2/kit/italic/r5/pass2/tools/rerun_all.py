"""Round 5 · pass 2: THE command that makes every stored key, table, reading and sheet of pass2/ (pass 2b).

    cd core/parts/italic/r5/pass2/tools && /usr/local/bin/python3.13 rerun_all.py

Steps, in order (each a separate process, so carry's K is set by its own --slant):
  build_his_s.py              the upright s = Mark's drawn roman s (idempotent: the old s stays in *Old_s keys)
  run_italic.py --slant 1/4   pass 2 at 14.04 deg -> GeistSerifItalic_<g> in src/geistserif_italic_14.json
  run_italic.py               pass 2 at 18.43 deg -> GeistSerifItalic_<g> in src/geistserif_italic_18.json
  italicsheet.py all          letter sheets, overview, word pages (18.43)
  italiccurv.py all           combs (18.43)
  score_p2.py, score_table_p2.py, score_smil_p2.py, sheets_p2.py all
The shipped switches are round_p2.py's module constants (TERMINAL, PSI, SERIF, I17, I17_TARGET, STEM_ENDS, SERIF_JOINT,
SIDE_HANDLES, SPINE_G2, PULL_K). round_p2.correct(gl, G) reproduces a stored key exactly: it reads K from the source.
The record of pass 2a (GeistSerifItalicPass2a_<g>, sheets/dev/*_pass2a.png) is not touched.
"""
import subprocess, sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
STEPS = [["build_his_s.py"], ["run_italic.py", "--slant", "1/4"], ["run_italic.py"], ["italicsheet.py", "all"], ["italiccurv.py", "all"],
         ["score_p2.py"], ["score_table_p2.py"], ["score_smil_p2.py"], ["sheets_p2.py", "all"]]
LOGS = {"run_italic.py --slant 1/4": "run_14.log", "run_italic.py": "run_18.log", "italicsheet.py all": "italicsheet_18.log",
        "italiccurv.py all": "curv_18.log", "score_p2.py": "score.log", "sheets_p2.py all": "sheets_p2.log", "build_his_s.py": "build_his_s.log"}
for st in STEPS:
    name = " ".join(st); t0 = time.time()
    log = os.path.join(HERE, "..", "readings", LOGS.get(name, st[0].replace(".py", ".log")))
    with open(log, "w") as f:
        subprocess.run([PY] + st, cwd=HERE, stdout=f, stderr=subprocess.STDOUT, check=True)
    print("%-28s %5.1f s  -> %s" % (name, time.time() - t0, os.path.relpath(log, HERE)), flush=True)
