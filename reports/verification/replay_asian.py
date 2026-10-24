"""Execute trusted captured source in a fresh directory and compare numerics."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from option_hedging.experiments.verify_run import verify_run

root=Path.cwd();original=root/'reports/examples/v2-asian'
assert verify_run(original)['source_recoverable']
recovered=root/'reports/verification/asian-execution/recovered'
index=2
while recovered.exists():
    recovered=root/f'reports/verification/asian-execution/recovered-{index}'
    index+=1
recovered.mkdir()
with zipfile.ZipFile(original/'source_snapshot.zip') as z:
    metadata=json.loads(z.read('SNAPSHOT.json'))
    for name,pin in metadata['runtime_versions'].items():assert version(name)==pin,(name,pin)
    z.extractall(recovered)
env=dict(os.environ,PYTHONPATH=str(recovered/'src'),
         MPLCONFIGDIR='/private/tmp/option-hedging-mpl-cache',XDG_CACHE_HOME='/private/tmp/option-hedging-cache')
probe=subprocess.run([sys.executable,'-c','import option_hedging.experiments.asian_study as m; print(m.__file__)'],
                     cwd=recovered,env=env,capture_output=True,text=True,check=True)
module_path=Path(probe.stdout.strip()).resolve()
assert module_path.is_relative_to(recovered/'src'),module_path
with (root/'reports/verification/asian-execution/replay.log').open('w') as log:
    result=subprocess.run([sys.executable,'-W','error','-m','option_hedging.experiments.asian_study',
                           '--config','input_config.toml','--output-dir','replay-output'],cwd=recovered,env=env,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,'See replay.log'
replay=recovered/'replay-output'
files=['estimates.csv','scramble_estimates.csv','reference_checks.csv','reference_summary.csv',
       'metrics.csv','paired_comparisons.csv','summary.json','effective_config.json','input_config.toml']
comparisons=[]
for name in files:
    a=(original/name).read_bytes();b=(replay/name).read_bytes()
    comparisons.append(dict(file=name,byte_identical=a==b,original_sha256=hashlib.sha256(a).hexdigest(),replay_sha256=hashlib.sha256(b).hexdigest()))
assert all(row['byte_identical'] for row in comparisons),comparisons
ma=json.loads((original/'manifest.json').read_text());mb=json.loads((replay/'manifest.json').read_text())
assert ma['source_hashes']==mb['source_hashes']
assert ma['numerical_acceptance']==mb['numerical_acceptance']
proof=dict(imported_module_path=str(module_path),runtime_versions=metadata['runtime_versions'],
    original_integrity=verify_run(original),replay_integrity=verify_run(replay),
    source_hashes_identical=True,numerical_acceptance_identical=True,comparisons=comparisons,
    exclusions=['stage_timings.csv','benchmark.csv','allocations.csv','figures','manifest artifact hashes for excluded observations'],
    note='Numerical replay in recorded local environment; not a portability or authenticity guarantee.')
(root/'reports/verification/v2-asian-replay.json').write_text(json.dumps(proof,indent=2,allow_nan=False)+'\n')
print('Recovered-source replay:',len(comparisons),'byte-identical numerical/input artifacts')
