import bittensor as bt

def generate_signature(wallet: bt.wallet, message: str):
    keypair = wallet.hotkey
    signature = keypair.sign(data=message)
    return signature.hex()

