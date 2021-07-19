import binascii
import uuid
from typing import List

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

import hashlib

"""
Class to represent a transaction inside a block
The public key is the address of the user
"""


class Transaction:
    # Creates a transaction object, where
    # keys are of type cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey(/RSAPublicKey)
    # amount = floating point
    def __init__(self, sender_public_key, sender_private_key, recipient_public_key, amount, uuid):
        self.sender_public_key = sender_public_key
        self.sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.uuid = uuid
        self.signature = ""

    # Function returns a dictionary of this transaction, without the private key
    def to_binary_dict(self) -> dict:
        return {
            "sender_public_key": self.sender_public_key,
            "recipient_public_key": self.recipient_public_key,
            "amount": self.amount,
            "uuid": self.uuid
        }

    def to_ascii_dict(self) -> dict:
        return {
            "sender_public_key": binary_to_ascii(
                self.sender_public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)),
            "recipient_public_key": binary_to_ascii(
                self.recipient_public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)),
            "amount": self.amount,
            "uuid": str(self.uuid)
        }

    # Function converts this object to a string, without the private key
    def __str__(self) -> str:
        return str(self.to_ascii_dict())

    # Function creates a signature of this transaction, signed by the private key of the sender
    def sign(self):
        self.signature = self.sender_private_key.sign(
            str(self).encode("ascii"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def is_valid(self) -> bool:
        try:
            self.sender_public_key.verify(
                self.signature,
                str(self).encode("ascii"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False


class Block:
    def __init__(self, transactions: List[Transaction], previous_block_hash: str):
        self.transactions = transactions
        self.proof_of_work = 0
        self.previous_block_hash = previous_block_hash
        self.uuid = uuid.uuid4()

    def hash(self) -> str:
        hash_creator = hashlib.sha256()
        for transaction in self.transactions:
            hash_creator.update(str(transaction).encode("ascii"))
        hash_creator.update(bytes.fromhex(self.previous_block_hash))
        hash_creator.update(str(self.proof_of_work).encode("ascii"))
        hash_creator.update(str(self.uuid).encode("utf-8"))
        return hash_creator.digest().hex()

    def is_valid(self) -> bool:
        return all(transaction.is_valid() for transaction in self.transactions)

    # Function converts this object to a string, without the private key
    def __str__(self) -> str:
        return str(dict(self))

    # For str()
    def __iter__(self):
        yield "uuid", str(self.uuid)
        yield "transactions", [trans.to_ascii_dict() for trans in self.transactions]
        yield "previous_block_hash", self.previous_block_hash
        yield "proof_of_work", self.proof_of_work

    @staticmethod
    def genesis_block():
        hash_creator = hashlib.sha256()
        hash_creator.update(b"0")  # Value from constructor
        return Block([], hash_creator.digest().hex())


class BlockChain:
    def __init__(self):
        self.transactions = []
        self.minable_blocks = []
        self.chain = [Block.genesis_block()]
        self.nodes = set()
        self.node_uuid = uuid.uuid4()

    max_transactions_const = 3

    def create_block(self):
        if len(self.transactions) < 1:
            print("Not enough transactions to make a block")
            return None

        # Get the max amount of transactions that can fit on the block that are not already in other minable blocks
        # First find the transactions currently being mined
        transactions_currently_mining = []
        for block in self.minable_blocks:
            transactions_currently_mining.extend(block.transactions)

        max_transactions = self.transactions[:BlockChain.max_transactions_const]
        transactions = []
        # now check
        for transaction in max_transactions:
            if transaction not in transactions_currently_mining:
                transactions.append(transaction)

        prev_block_hash = self.chain[-1].hash()
        new_block = Block(transactions, prev_block_hash)

        self.minable_blocks.append(new_block)
        return new_block

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
        pass


class Wallet:
    def __init__(self, generate_keys=True):
        self.private_key = self.public_key = None
        if generate_keys:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=512
            )
            self.public_key = self.private_key.public_key()

    # Function creates a new Wallet object with private/public keys given in an ascii format
    @classmethod
    def from_ascii_keys(cls, private_key, public_key):
        wallet = cls(False)
        wallet.private_key = ascii_key_to_private_key(private_key)
        wallet.public_key = ascii_key_to_public_key(public_key)
        return wallet

    @classmethod
    def from_binary_keys(cls, private_key, public_key):
        wallet = cls(False)
        wallet.private_key = serialization.load_der_private_key(private_key, None)
        wallet.public_key = serialization.load_der_public_key(public_key)
        return wallet

    # Function returns both (private key, public key) pair in bytes
    def keys_to_bytes(self):
        return (self.private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()),
                self.public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))

    # Function returns both (private key,public key) pair in an ascii encoding
    def keys_to_ascii(self):
        return tuple(binary_to_ascii(key) for key in self.keys_to_bytes())


# Function returns a ascii key
def binary_to_ascii(binary_item):
    return binascii.hexlify(binary_item).decode("ascii")


def ascii_to_binary(ascii_item):
    return binascii.unhexlify(ascii_item)


def ascii_key_to_public_key(ascii_key):
    return serialization.load_der_public_key(binascii.unhexlify(ascii_key))


# Function loads an ascii key to form a cryptography.hazmat RSA private key
def ascii_key_to_private_key(ascii_key, password=None):
    return serialization.load_der_private_key(binascii.unhexlify(ascii_key), password)


def serializer(obj):
    if isinstance(obj, Transaction):
        return obj.to_ascii_dict()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Block):
        return str(obj)
    return obj.__dict__
