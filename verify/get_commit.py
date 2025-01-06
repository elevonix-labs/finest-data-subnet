import bittensor as bt
subtensor = bt.subtensor(network='finney')
commit = subtensor.get_commitment(netuid=250, uid=1)
print(commit)
version = bt.__version__
cr3_info = subtensor.get_current_weight_commit_info(netuid = 1)
print(version)