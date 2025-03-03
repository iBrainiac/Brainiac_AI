import json
from swarm import Agent
from cdp import *
from typing import List, Dict, Any
import os
from openai import OpenAI
from decimal import Decimal
from typing import Union
from web3 import Web3
from web3.exceptions import ContractLogicError
from cdp.errors import ApiError, UnsupportedAssetError
import requests

# Get configuration from environment variables
API_KEY_NAME = os.environ.get("CDP_API_KEY_NAME")
PRIVATE_KEY = os.environ.get("CDP_PRIVATE_KEY", "").replace('\\n', '\n')
MORALIS_API_KEY = os.environ.get("MORALIS_API_KEY")

# Configure CDP with environment variables
Cdp.configure(API_KEY_NAME, PRIVATE_KEY)

# Create a new wallet on the Base Sepolia testnet
# You could make this a function for the agent to create a wallet on any network
# If you want to use Base Mainnet, change Wallet.create() to Wallet.create(network_id="base-mainnet")
# see https://docs.cdp.coinbase.com/mpc-wallet/docs/wallets for more information
# agent_wallet = Wallet.create(network_id="base-mainnet")



# NOTE: the wallet is not currently persisted, meaning that it will be deleted after the agent is stopped. To persist the wallet, see https://docs.cdp.coinbase.com/mpc-wallet/docs/wallets#developer-managed-wallets
# Here's an example of how to persist the wallet:
# WARNING: This is for development only - implement secure storage in production!

# # Export wallet data (contains seed and wallet ID)
# wallet_data = agent_wallet.export_data()
# wallet_dict = wallet_data.to_dict()

# # Example of saving to encrypted local file
# file_path = "wallet_seed.json"
# agent_wallet.save_seed(file_path, encrypt=True)
# print(f"Seed for wallet {agent_wallet.id} saved to {file_path}")

# Create a new wallet on the Base Sepolia testnet
agent_wallet = Wallet.create(network_id="base-sepolia")

# Save the wallet seed for future use
file_path = "wallet_seed.json"
agent_wallet.save_seed(file_path, encrypt=True)
print(f"Seed for wallet {agent_wallet.id} saved to {file_path} (Base Sepolia)")

# Example of importing previously exported wallet data:
# imported_wallet = Wallet.import_data(wallet_dict)

# Request funds from the faucet (only works on testnet)
faucet = agent_wallet.faucet()
print(f"Faucet transaction: {faucet}")
print(f"Agent wallet address: {agent_wallet.default_address.address_id}")


# Function to create a new ERC-20 token
def create_token(name, symbol, initial_supply):
    """
    Create a new ERC-20 token.

    Args:
        name (str): The name of the token
        symbol (str): The symbol of the token
        initial_supply (int): The initial supply of tokens

    Returns:
        str: A message confirming the token creation with details
    """
    deployed_contract = agent_wallet.deploy_token(name, symbol, initial_supply)
    deployed_contract.wait()
    return f"Token {name} ({symbol}) created with initial supply of {initial_supply} and contract address {deployed_contract.contract_address}"


# Function to request ETH from the faucet (testnet only)
def request_eth_from_faucet():
    """
    Request ETH from the Base Sepolia testnet faucet.

    Returns:
        str: Status message about the faucet request
    """
    if agent_wallet.network_id == "base-mainnet":
        return "Error: The faucet is only available on Base Sepolia testnet."

    faucet_tx = agent_wallet.faucet()
    return f"Requested ETH from faucet. Transaction: {faucet_tx}"


# Function to generate art using DALL-E (requires separate OpenAI API key)
def generate_art(prompt):
    """
    Generate art using DALL-E based on a text prompt.

    Args:
        prompt (str): Text description of the desired artwork

    Returns:
        str: Status message about the art generation, including the image URL if successful
    """
    try:
        client = OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        return f"Generated artwork available at: {image_url}"

    except Exception as e:
        return f"Error generating artwork: {str(e)}"


# Function to deploy an ERC-721 NFT contract
def deploy_nft(name, symbol, base_uri):
    """
    Deploy an ERC-721 NFT contract.

    Args:
        name (str): Name of the NFT collection
        symbol (str): Symbol of the NFT collection
        base_uri (str): Base URI for token metadata

    Returns:
        str: Status message about the NFT deployment, including the contract address
    """
    try:
        deployed_nft = agent_wallet.deploy_nft(name, symbol, base_uri)
        deployed_nft.wait()
        contract_address = deployed_nft.contract_address

        return f"Successfully deployed NFT contract '{name}' ({symbol}) at address {contract_address} with base URI: {base_uri}"

    except Exception as e:
        return f"Error deploying NFT contract: {str(e)}"


# Function to mint an NFT
def mint_nft(contract_address, mint_to):
    """
    Mint an NFT to a specified address.

    Args:
        contract_address (str): Address of the NFT contract
        mint_to (str): Address to mint NFT to

    Returns:
        str: Status message about the NFT minting
    """
    try:
        mint_args = {"to": mint_to, "quantity": "1"}

        mint_invocation = agent_wallet.invoke_contract(
            contract_address=contract_address, method="mint", args=mint_args)
        mint_invocation.wait()

        return f"Successfully minted NFT to {mint_to}"

    except Exception as e:
        return f"Error minting NFT: {str(e)}"


# Function to swap assets (only works on Base Mainnet)
def swap_assets(amount: Union[int, float, Decimal], from_asset_id: str,
                to_asset_id: str):
    """
    Swap one asset for another using the trade function.
    This function only works on Base Mainnet.

    Args:
        amount (Union[int, float, Decimal]): Amount of the source asset to swap
        from_asset_id (str): Source asset identifier
        to_asset_id (str): Destination asset identifier

    Returns:
        str: Status message about the swap
    """
    if agent_wallet.network_id != "base-mainnet":
        return "Error: Asset swaps are only available on Base Mainnet. Current network is not Base Mainnet."

    try:
        trade = agent_wallet.trade(amount, from_asset_id, to_asset_id)
        trade.wait()
        return f"Successfully swapped {amount} {from_asset_id} for {to_asset_id}"
    except Exception as e:
        return f"Error swapping assets: {str(e)}"


# Contract addresses for Basenames
BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_MAINNET = "0x4cCb0BB02FCABA27e82a56646E81d8c5bC4119a5"
BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_TESTNET = "0x49aE3cC2e3AA768B1e5654f5D3C6002144A59581"
L2_RESOLVER_ADDRESS_MAINNET = "0xC6d566A56A1aFf6508b41f6c90ff131615583BCD"
L2_RESOLVER_ADDRESS_TESTNET = "0x6533C94869D28fAA8dF77cc63f9e2b2D6Cf77eBA"


# Function to create registration arguments for Basenames
def create_register_contract_method_args(base_name: str, address_id: str,
                                         is_mainnet: bool) -> dict:
    """
    Create registration arguments for Basenames.

    Args:
        base_name (str): The Basename (e.g., "example.base.eth" or "example.basetest.eth")
        address_id (str): The Ethereum address
        is_mainnet (bool): True if on mainnet, False if on testnet

    Returns:
        dict: Formatted arguments for the register contract method
    """
    w3 = Web3()

    resolver_contract = w3.eth.contract(abi=l2_resolver_abi)

    name_hash = w3.ens.namehash(base_name)

    address_data = resolver_contract.encode_abi("setAddr",
                                                args=[name_hash, address_id])

    name_data = resolver_contract.encode_abi("setName",
                                             args=[name_hash, base_name])

    register_args = {
        "request": [
            base_name.replace(".base.eth" if is_mainnet else ".basetest.eth",
                              ""),
            address_id,
            "31557600",  # 1 year in seconds
            L2_RESOLVER_ADDRESS_MAINNET
            if is_mainnet else L2_RESOLVER_ADDRESS_TESTNET,
            [address_data, name_data],
            True
        ]
    }

    return register_args


# Function to register a basename
def register_basename(basename: str, amount: float = 0.002):
    """
    Register a basename for the agent's wallet.

    Args:
        basename (str): The basename to register (e.g. "myname.base.eth" or "myname.basetest.eth")
        amount (float): Amount of ETH to pay for registration (default 0.002)

    Returns:
        str: Status message about the basename registration
    """
    address_id = agent_wallet.default_address.address_id
    is_mainnet = agent_wallet.network_id == "base-mainnet"

    suffix = ".base.eth" if is_mainnet else ".basetest.eth"
    if not basename.endswith(suffix):
        basename += suffix

    register_args = create_register_contract_method_args(
        basename, address_id, is_mainnet)

    try:
        contract_address = (BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_MAINNET
                            if is_mainnet else
                            BASENAMES_REGISTRAR_CONTROLLER_ADDRESS_TESTNET)

        invocation = agent_wallet.invoke_contract(
            contract_address=contract_address,
            method="register",
            args=register_args,
            abi=registrar_abi,
            amount=amount,
            asset_id="eth",
        )
        invocation.wait()
        return f"Successfully registered basename {basename} for address {address_id}"
    except ContractLogicError as e:
        return f"Error registering basename: {str(e)}"
    except Exception as e:
        return f"Unexpected error registering basename: {str(e)}"


def get_token_metadata(token_address: str) -> str:
    """
    Fetch metadata for an ERC-20 token using the Moralis API.
    Automatically determines if the network is mainnet or testnet.

    Args:
        token_address (str): The address of the ERC-20 token

    Returns:
        str: A message with the token metadata or an error message if unsuccessful
    """
    # Read the Moralis API key from the environment
    if not MORALIS_API_KEY:
        return "Error: Moralis API key is missing. Please set the MORALIS_API_KEY environment variable."

    # Determine the network dynamically based on the agent's current network ID
    is_mainnet = agent_wallet.network_id in ["base", "base-mainnet"]
    chain = "base" if is_mainnet else "base sepolia"

    # API endpoint and headers
    url = "https://deep-index.moralis.io/api/v2.2/erc20/metadata"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": chain,
        "addresses[0]": token_address
    }

    # Fetch token metadata
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        metadata = response.json()

        if metadata:
            token_data = metadata[0]
            return (
                f"Token Name: {token_data.get('name')}\n"
                f"Symbol: {token_data.get('symbol')}\n"
                f"Decimals: {token_data.get('decimals')}\n"
                f"Total Supply: {token_data.get('total_supply_formatted')}\n"
                f"Contract Address: {token_data.get('address')}\n"
                f"Verified: {token_data.get('verified_contract')}\n"
                f"Logo URL: {token_data.get('logo')}\n"
            )
        else:
            return "No metadata found for the provided token address."

    except requests.exceptions.RequestException as e:
        return f"Error fetching token metadata: {str(e)}"


def get_wallet_tokens() -> str:
    """
    Fetch the list of ERC-20 tokens held by the agent's wallet using the Moralis API.

    Returns:
        str: A message with the list of tokens and balances or an error message if unsuccessful
    """
    # Get the agent's wallet address
    address_id = agent_wallet.default_address.address_id

    # Determine the network dynamically based on the agent's current network ID
    is_mainnet = agent_wallet.network_id in ["base", "base-mainnet"]
    chain = "base" if is_mainnet else "base sepolia"

    # API endpoint and headers
    url = f"https://deep-index.moralis.io/api/v2.2/wallets/{address_id}/tokens"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": chain
    }

    # Fetch wallet token balances
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        tokens = response.json().get("result", [])

        # Format the output
        if tokens:
            token_list = "\n".join(
                [
                    f"Token: {token['name']} ({token['symbol']})\n"
                    f"Balance: {token['balance_formatted']} {token['symbol']}\n"
                    f"Contract Address: {token['token_address']}\n"
                    f"Verified: {'Yes' if token['verified_contract'] else 'No'}\n"
                    f"Price (USD): {token['usd_price'] or 'N/A'}\n"
                    for token in tokens
                ]
            )
            return f"Tokens held by {address_id}:\n{token_list}"
        else:
            return f"No tokens found for wallet {address_id}."

    except requests.exceptions.RequestException as e:
        return f"Error fetching wallet tokens: {str(e)}"


def get_trending_tokens(security_score=80, min_market_cap=100000) -> str:
    """
    Fetch trending tokens with a minimum security score and market cap.

    Args:
        security_score (int): Minimum security score for tokens
        min_market_cap (int): Minimum market cap for tokens

    Returns:
        str: Trending token information or an error message
    """
    # Check if Moralis API key is available
    if not MORALIS_API_KEY:
        return "Error: Moralis API key is missing. Please set the MORALIS_API_KEY environment variable."
    
    # Determine the network dynamically based on the agent's current network ID
    is_mainnet = agent_wallet.network_id in ["base", "base-mainnet"]
    chain = "base" if is_mainnet else "base sepolia"
    
    url = "https://deep-index.moralis.io/api/v2.2/discovery/tokens/trending"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": chain,  # Use the correct chain based on network
        "security_score": security_score,
        "min_market_cap": min_market_cap
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        tokens = response.json()
        
        # Check if tokens were returned
        if not tokens:
            return "No trending tokens found matching the criteria. Try adjusting the security score or market cap parameters."

        # Format the output
        token_info = "\n".join(
            [
                f"Token Name: {token.get('token_name', 'Unknown')} ({token.get('token_symbol', 'Unknown')})\n"
                f"Price (USD): {token.get('price_usd', 'N/A')}\n"
                f"Market Cap: {token.get('market_cap', 'N/A')}\n"
                f"Security Score: {token.get('security_score', 'N/A')}\n"
                f"Logo: {token.get('token_logo', 'N/A')}\n"
                for token in tokens
            ]
        )
        return f"Trending Tokens:\n{token_info}"

    except requests.exceptions.RequestException as e:
        return f"Error fetching trending tokens: {str(e)}"
    except ValueError as e:
        return f"Error parsing response: {str(e)}"
    except Exception as e:
        return f"Unexpected error retrieving trending tokens: {str(e)}"

def get_wallet_pnl() -> str:
    """
    Retrieve PnL information for the agent's wallet assets.

    Returns:
        str: Wallet PnL data or an error message if unsuccessful
    """
    # Get the agent's wallet address
    address_id = agent_wallet.default_address.address_id

    url = f"https://deep-index.moralis.io/api/v2.2/wallets/{address_id}/profitability"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": "base"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        pnl_data = response.json().get("result", [])

        # Format the output
        if pnl_data:
            pnl_info = "\n".join(
                [
                    f"Token: {entry['name']} ({entry['symbol']})\n"
                    f"Total Invested: ${entry['total_usd_invested']}\n"
                    f"Realized Profit: ${entry['realized_profit_usd']}\n"
                    f"Avg Buy Price: ${entry['avg_buy_price_usd']}\n"
                    f"Total Tokens Bought: {entry['total_tokens_bought']}\n"
                    f"Logo: {entry['logo']}\n"
                    for entry in pnl_data
                ]
            )
            return f"Wallet PnL for {address_id}:\n{pnl_info}"
        else:
            return "No PnL data found for the wallet."

    except requests.exceptions.RequestException as e:
        return f"Error fetching wallet PnL: {str(e)}"


def get_wallet_nfts() -> str:
    """
    Fetch the raw response of NFTs held by the agent's wallet on the Base blockchain.
    Automatically determines if the network is mainnet or testnet.

    Returns:
        str: Raw JSON response of NFTs or an error message if unsuccessful.
    """
    # Get the agent's wallet address
    wallet_address = agent_wallet.default_address.address_id

    # Determine the network dynamically based on the agent's current network ID
    is_mainnet = agent_wallet.network_id in ["base", "base-mainnet"]
    chain = "base" if is_mainnet else "base sepolia"

    # API endpoint and headers
    url = f"https://deep-index.moralis.io/api/v2.2/{wallet_address}/nft"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": chain,
        "format": "decimal",
        "media_items": "false"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.text  # Return the raw JSON response as text

    except requests.exceptions.RequestException as e:
        return f"Error fetching wallet NFTs: {str(e)}"

def get_token_pairs(token_address: str) -> str:
    """
    Fetch trading pairs for a specific ERC-20 token on the Base blockchain.
    Automatically determines if the network is mainnet or testnet.

    Args:
        token_address (str): The address of the ERC-20 token.

    Returns:
        str: Information about trading pairs or an error message if unsuccessful.
    """
    # Determine the network dynamically based on the agent's current network ID
    is_mainnet = agent_wallet.network_id in ["base", "base-mainnet"]
    chain = "base" if is_mainnet else "base sepolia"

    # API endpoint and headers
    url = f"https://deep-index.moralis.io/api/v2.2/erc20/{token_address}/pairs"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": chain
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        pairs = response.json().get("pairs", [])

        # Format the output
        if pairs:
            pairs_info = "\n".join(
                [
                    f"Pair: {pair['pair_label']}\n"
                    f"Price (USD): {pair['usd_price']}\n"
                    f"24hr Price Change (%): {pair['usd_price_24hr_percent_change']}\n"
                    f"Liquidity (USD): {pair['liquidity_usd']}\n"
                    f"Exchange Address: {pair['exchange_address']}\n"
                    f"Base Token: {pair['pair'][0]['token_name']} ({pair['pair'][0]['token_symbol']})\n"
                    f"Quote Token: {pair['pair'][1]['token_name']} ({pair['pair'][1]['token_symbol']})\n"
                    for pair in pairs
                ]
            )
            return f"Trading pairs for token {token_address}:\n{pairs_info}"
        else:
            return f"No trading pairs found for token {token_address}."

    except requests.exceptions.RequestException as e:
        return f"Error fetching token pairs: {str(e)}"

def get_token_details(token_address: str) -> str:
    """
    Fetch detailed information about a specific ERC-20 token on the Base blockchain.
    Automatically determines if the network is mainnet or testnet.

    Args:
        token_address (str): The address of the ERC-20 token.

    Returns:
        str: Information about the token or an error message if unsuccessful.
    """
    # Determine the network dynamically based on the agent's current network ID
    is_mainnet = agent_wallet.network_id in ["base", "base-mainnet"]
    chain = "base" if is_mainnet else "base sepolia"

    # API endpoint and headers
    url = f"https://deep-index.moralis.io/api/v2.2/discovery/token"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    params = {
        "chain": chain,
        "token_address": token_address
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        token_data = response.json()

        # Format the output
        token_info = (
            f"Token Name: {token_data.get('token_name')}\n"
            f"Symbol: {token_data.get('token_symbol')}\n"
            f"Price (USD): {token_data.get('price_usd')}\n"
            f"Market Cap: {token_data.get('market_cap')}\n"
            f"Security Score: {token_data.get('security_score')}\n"
            f"Token Age (days): {token_data.get('token_age_in_days')}\n"
            f"On-Chain Strength Index: {token_data.get('on_chain_strength_index')}\n"
            f"1-Day Holders Change: {token_data['holders_change'].get('1d')}\n"
            f"1-Day Volume Change (USD): {token_data['volume_change_usd'].get('1d')}\n"
            f"1-Month Price Change (%): {token_data['price_percent_change_usd'].get('1M')}\n"
            f"Logo: {token_data.get('token_logo')}\n"
        )
        return token_info

    except requests.exceptions.RequestException as e:
        return f"Error fetching token details: {str(e)}"


# Create the Based Agent with all available functions
based_agent = Agent(
    name="Based Agent",
    instructions=(
        "You are a specialized investment agent on the Base Layer 2 blockchain, designed to optimize an existing portfolio by analyzing and trading trending tokens. "
        "Your primary goal is to identify profitable tokens in the market, review wallet balances, and make calculated swap decisions to enhance the portfolio value. "
        "Follow these steps when making investment decisions:\n"
        "\n1. Use trending data to identify promising tokens with potential profit.\n"
        "2. For each trending token, retrieve detailed information to evaluate its market cap, liquidity, and security.\n"
        "3. Check the wallet balance to understand the available assets and decide on a safe percentage to invest.\n"
        "4. Execute swaps to acquire trending tokens, ensuring the chosen amount aligns with profitability goals and balance management.\n"
        "Make data-driven decisions based on token performance, wallet balance, and profitability, while maximizing portfolio value with each trade. "
        "Use all available functions to analyze market trends, asset details, and wallet metrics to act with precision and efficiency."
    ),
    functions=[
        create_token,
        request_eth_from_faucet,
        # generate_art,  # Uncomment this line if you have configured the OpenAI API
        deploy_nft,
        mint_nft,
        swap_assets,
        register_basename,
        get_token_metadata,
        get_wallet_tokens,
        get_trending_tokens,
        get_wallet_pnl,
        get_wallet_nfts,
        get_token_pairs,
        get_token_details,
    ],
)

# add the following import to the top of the file, add the code below it, and add the new functions to the based_agent.functions list

# from twitter_utils import TwitterBot

# # Initialize TwitterBot with your credentials
# twitter_bot = TwitterBot(
#     api_key="your_api_key",
#     api_secret="your_api_secret",
#     access_token="your_access_token",
#     access_token_secret="your_access_token_secret"
# )

# # Add these new functions to your existing functions list

# def post_to_twitter(content: str):
#     """
#     Post a message to Twitter.
#
#     Args:
#         content (str): The content to tweet
#
#     Returns:
#         str: Status message about the tweet
#     """
#     return twitter_bot.post_tweet(content)

# def check_twitter_mentions():
#     """
#     Check recent Twitter mentions.
#
#     Returns:
#         str: Formatted string of recent mentions
#     """
#     mentions = twitter_bot.read_mentions()
#     if not mentions:
#         return "No recent mentions found"

#     result = "Recent mentions:\n"
#     for mention in mentions:
#         if 'error' in mention:
#             return f"Error checking mentions: {mention['error']}"
#         result += f"- @{mention['user']}: {mention['text']}\n"
#     return result

# def reply_to_twitter_mention(tweet_id: str, content: str):
#     """
#     Reply to a specific tweet.
#
#     Args:
#         tweet_id (str): ID of the tweet to reply to
#         content (str): Content of the reply
#
#     Returns:
#         str: Status message about the reply
#     """
#     return twitter_bot.reply_to_tweet(tweet_id, content)

# def search_twitter(query: str):
#     """
#     Search for tweets matching a query.
#
#     Args:
#         query (str): Search query
#
#     Returns:
#         str: Formatted string of matching tweets
#     """
#     tweets = twitter_bot.search_tweets(query)
#     if not tweets:
#         return f"No tweets found matching query: {query}"

#     result = f"Tweets matching '{query}':\n"
#     for tweet in tweets:
#         if 'error' in tweet:
#             return f"Error searching tweets: {tweet['error']}"
#         result += f"- @{tweet['user']}: {tweet['text']}\n"
#     return result

# ABIs for smart contracts (used in basename registration)
l2_resolver_abi = [{
    "inputs": [{
        "internalType": "bytes32",
        "name": "node",
        "type": "bytes32"
    }, {
        "internalType": "address",
        "name": "a",
        "type": "address"
    }],
    "name":
    "setAddr",
    "outputs": [],
    "stateMutability":
    "nonpayable",
    "type":
    "function"
}, {
    "inputs": [{
        "internalType": "bytes32",
        "name": "node",
        "type": "bytes32"
    }, {
        "internalType": "string",
        "name": "newName",
        "type": "string"
    }],
    "name":
    "setName",
    "outputs": [],
    "stateMutability":
    "nonpayable",
    "type":
    "function"
}]

registrar_abi = [{
    "inputs": [{
        "components": [{
            "internalType": "string",
            "name": "name",
            "type": "string"
        }, {
            "internalType": "address",
            "name": "owner",
            "type": "address"
        }, {
            "internalType": "uint256",
            "name": "duration",
            "type": "uint256"
        }, {
            "internalType": "address",
            "name": "resolver",
            "type": "address"
        }, {
            "internalType": "bytes[]",
            "name": "data",
            "type": "bytes[]"
        }, {
            "internalType": "bool",
            "name": "reverseRecord",
            "type": "bool"
        }],
        "internalType":
        "struct RegistrarController.RegisterRequest",
        "name":
        "request",
        "type":
        "tuple"
    }],
    "name":
    "register",
    "outputs": [],
    "stateMutability":
    "payable",
    "type":
    "function"
}]

# To add a new function:
# 1. Define your function above (follow the existing pattern)
# 2. Add appropriate error handling
# 3. Add the function to the based_agent's functions list
# 4. If your function requires new imports or global variables, add them at the top of the file
# 5. Test your new function thoroughly before deploying

# Example of adding a new function:
# def my_new_function(param1, param2):
#     """
#     Description of what this function does.
#
#     Args:
#         param1 (type): Description of param1
#         param2 (type): Description of param2
#
#     Returns:
#         type: Description of what is returned
#     """
#     try:
#         # Your function logic here
#         result = do_something(param1, param2)
#         return f"Operation successful: {result}"
#     except Exception as e:
#         return f"Error in my_new_function: {str(e)}"

# Then add to based_agent.functions:
# based_agent = Agent(
#     ...
#     functions=[
#         ...
#         my_new_function,
#     ],
# )