#!/usr/bin/env python

# PyWallet 1.2.1 (Public Domain)
# http://github.com/joric/pywallet
# Most of the actual PyWallet code placed in the public domain.
# PyWallet includes portions of free software, listed below.

# BitcoinTools (wallet.dat handling code, MIT License)
# https://github.com/gavinandresen/bitcointools
# Copyright (c) 2010 Gavin Andresen

# python-ecdsa (EC_KEY implementation, MIT License)
# http://github.com/warner/python-ecdsa
# "python-ecdsa" Copyright (c) 2010 Brian Warner
# Portions written in 2005 by Peter Pearson and placed in the public domain.

# SlowAES (aes.py code, Apache 2 License)
# http://code.google.com/p/slowaes/
# Copyright (c) 2008, Josh Davis (http://www.josh-davis.org), 
# Alex Martelli (http://www.aleax.it)
# Ported from C code written by Laurent Haan (http://www.progressive-coding.com)

import os, sys, time
import json
import logging
import struct
import StringIO
import traceback
import socket
import types
import string
import exceptions
import hashlib
import random
import math

max_version = 60000
addrtype = 0
json_db = {}
private_keys = []
password = None

def determine_db_dir():
    import os
    import os.path
    import platform
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/Bitcoin/")
    elif platform.system() == "Windows":
        return os.path.join(os.environ['APPDATA'], "Bitcoin")
    return os.path.expanduser("~/.bitcoin")

# from the SlowAES project, http://code.google.com/p/slowaes (aes.py)

def append_PKCS7_padding(s):
    """return s padded to a multiple of 16-bytes by PKCS7 padding"""
    numpads = 16 - (len(s)%16)
    return s + numpads*chr(numpads)

def strip_PKCS7_padding(s):
    """return s stripped of PKCS7 padding"""
    if len(s)%16 or not s:
        raise ValueError("String of len %d can't be PCKS7-padded" % len(s))
    numpads = ord(s[-1])
    if numpads > 16:
        raise ValueError("String ending with %r can't be PCKS7-padded" % s[-1])
    return s[:-numpads]

class AES(object):
    # valid key sizes
    keySize = dict(SIZE_128=16, SIZE_192=24, SIZE_256=32)

    # Rijndael S-box
    sbox =  [0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67,
            0x2b, 0xfe, 0xd7, 0xab, 0x76, 0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59,
            0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0, 0xb7,
            0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1,
            0x71, 0xd8, 0x31, 0x15, 0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05,
            0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75, 0x09, 0x83,
            0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29,
            0xe3, 0x2f, 0x84, 0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b,
            0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf, 0xd0, 0xef, 0xaa,
            0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c,
            0x9f, 0xa8, 0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc,
            0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2, 0xcd, 0x0c, 0x13, 0xec,
            0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19,
            0x73, 0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee,
            0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb, 0xe0, 0x32, 0x3a, 0x0a, 0x49,
            0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
            0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4,
            0xea, 0x65, 0x7a, 0xae, 0x08, 0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6,
            0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a, 0x70,
            0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9,
            0x86, 0xc1, 0x1d, 0x9e, 0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e,
            0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf, 0x8c, 0xa1,
            0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0,
            0x54, 0xbb, 0x16]

    # Rijndael Inverted S-box
    rsbox = [0x52, 0x09, 0x6a, 0xd5, 0x30, 0x36, 0xa5, 0x38, 0xbf, 0x40, 0xa3,
            0x9e, 0x81, 0xf3, 0xd7, 0xfb , 0x7c, 0xe3, 0x39, 0x82, 0x9b, 0x2f,
            0xff, 0x87, 0x34, 0x8e, 0x43, 0x44, 0xc4, 0xde, 0xe9, 0xcb , 0x54,
            0x7b, 0x94, 0x32, 0xa6, 0xc2, 0x23, 0x3d, 0xee, 0x4c, 0x95, 0x0b,
            0x42, 0xfa, 0xc3, 0x4e , 0x08, 0x2e, 0xa1, 0x66, 0x28, 0xd9, 0x24,
            0xb2, 0x76, 0x5b, 0xa2, 0x49, 0x6d, 0x8b, 0xd1, 0x25 , 0x72, 0xf8,
            0xf6, 0x64, 0x86, 0x68, 0x98, 0x16, 0xd4, 0xa4, 0x5c, 0xcc, 0x5d,
            0x65, 0xb6, 0x92 , 0x6c, 0x70, 0x48, 0x50, 0xfd, 0xed, 0xb9, 0xda,
            0x5e, 0x15, 0x46, 0x57, 0xa7, 0x8d, 0x9d, 0x84 , 0x90, 0xd8, 0xab,
            0x00, 0x8c, 0xbc, 0xd3, 0x0a, 0xf7, 0xe4, 0x58, 0x05, 0xb8, 0xb3,
            0x45, 0x06 , 0xd0, 0x2c, 0x1e, 0x8f, 0xca, 0x3f, 0x0f, 0x02, 0xc1,
            0xaf, 0xbd, 0x03, 0x01, 0x13, 0x8a, 0x6b , 0x3a, 0x91, 0x11, 0x41,
            0x4f, 0x67, 0xdc, 0xea, 0x97, 0xf2, 0xcf, 0xce, 0xf0, 0xb4, 0xe6,
            0x73 , 0x96, 0xac, 0x74, 0x22, 0xe7, 0xad, 0x35, 0x85, 0xe2, 0xf9,
            0x37, 0xe8, 0x1c, 0x75, 0xdf, 0x6e , 0x47, 0xf1, 0x1a, 0x71, 0x1d,
            0x29, 0xc5, 0x89, 0x6f, 0xb7, 0x62, 0x0e, 0xaa, 0x18, 0xbe, 0x1b ,
            0xfc, 0x56, 0x3e, 0x4b, 0xc6, 0xd2, 0x79, 0x20, 0x9a, 0xdb, 0xc0,
            0xfe, 0x78, 0xcd, 0x5a, 0xf4 , 0x1f, 0xdd, 0xa8, 0x33, 0x88, 0x07,
            0xc7, 0x31, 0xb1, 0x12, 0x10, 0x59, 0x27, 0x80, 0xec, 0x5f , 0x60,
            0x51, 0x7f, 0xa9, 0x19, 0xb5, 0x4a, 0x0d, 0x2d, 0xe5, 0x7a, 0x9f,
            0x93, 0xc9, 0x9c, 0xef , 0xa0, 0xe0, 0x3b, 0x4d, 0xae, 0x2a, 0xf5,
            0xb0, 0xc8, 0xeb, 0xbb, 0x3c, 0x83, 0x53, 0x99, 0x61 , 0x17, 0x2b,
            0x04, 0x7e, 0xba, 0x77, 0xd6, 0x26, 0xe1, 0x69, 0x14, 0x63, 0x55,
            0x21, 0x0c, 0x7d]

    def getSBoxValue(self,num):
        """Retrieves a given S-Box Value"""
        return self.sbox[num]

    def getSBoxInvert(self,num):
        """Retrieves a given Inverted S-Box Value"""
        return self.rsbox[num]

    def rotate(self, word):
        """ Rijndael's key schedule rotate operation.

        Rotate a word eight bits to the left: eg, rotate(1d2c3a4f) == 2c3a4f1d
        Word is an char list of size 4 (32 bits overall).
        """
        return word[1:] + word[:1]

    # Rijndael Rcon
    Rcon = [0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36,
            0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97,
            0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72,
            0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66,
            0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04,
            0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d,
            0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3,
            0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61,
            0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a,
            0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40,
            0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc,
            0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5,
            0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a,
            0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d,
            0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c,
            0xd8, 0xab, 0x4d, 0x9a, 0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35,
            0x6a, 0xd4, 0xb3, 0x7d, 0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4,
            0xd3, 0xbd, 0x61, 0xc2, 0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc,
            0x83, 0x1d, 0x3a, 0x74, 0xe8, 0xcb, 0x8d, 0x01, 0x02, 0x04, 0x08,
            0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d, 0x9a,
            0x2f, 0x5e, 0xbc, 0x63, 0xc6, 0x97, 0x35, 0x6a, 0xd4, 0xb3, 0x7d,
            0xfa, 0xef, 0xc5, 0x91, 0x39, 0x72, 0xe4, 0xd3, 0xbd, 0x61, 0xc2,
            0x9f, 0x25, 0x4a, 0x94, 0x33, 0x66, 0xcc, 0x83, 0x1d, 0x3a, 0x74,
            0xe8, 0xcb ]

    def getRconValue(self, num):
        """Retrieves a given Rcon Value"""
        return self.Rcon[num]

    def core(self, word, iteration):
        """Key schedule core."""
        # rotate the 32-bit word 8 bits to the left
        word = self.rotate(word)
        # apply S-Box substitution on all 4 parts of the 32-bit word
        for i in range(4):
            word[i] = self.getSBoxValue(word[i])
        # XOR the output of the rcon operation with i to the first part
        # (leftmost) only
        word[0] = word[0] ^ self.getRconValue(iteration)
        return word

    def expandKey(self, key, size, expandedKeySize):
        """Rijndael's key expansion.

        Expands an 128,192,256 key into an 176,208,240 bytes key

        expandedKey is a char list of large enough size,
        key is the non-expanded key.
        """
        # current expanded keySize, in bytes
        currentSize = 0
        rconIteration = 1
        expandedKey = [0] * expandedKeySize

        # set the 16, 24, 32 bytes of the expanded key to the input key
        for j in range(size):
            expandedKey[j] = key[j]
        currentSize += size

        while currentSize < expandedKeySize:
            # assign the previous 4 bytes to the temporary value t
            t = expandedKey[currentSize-4:currentSize]

            # every 16,24,32 bytes we apply the core schedule to t
            # and increment rconIteration afterwards
            if currentSize % size == 0:
                t = self.core(t, rconIteration)
                rconIteration += 1
            # For 256-bit keys, we add an extra sbox to the calculation
            if size == self.keySize["SIZE_256"] and ((currentSize % size) == 16):
                for l in range(4): t[l] = self.getSBoxValue(t[l])

            # We XOR t with the four-byte block 16,24,32 bytes before the new
            # expanded key.  This becomes the next four bytes in the expanded
            # key.
            for m in range(4):
                expandedKey[currentSize] = expandedKey[currentSize - size] ^ \
                        t[m]
                currentSize += 1

        return expandedKey

    def addRoundKey(self, state, roundKey):
        """Adds (XORs) the round key to the state."""
        for i in range(16):
            state[i] ^= roundKey[i]
        return state

    def createRoundKey(self, expandedKey, roundKeyPointer):
        """Create a round key.
        Creates a round key from the given expanded key and the
        position within the expanded key.
        """
        roundKey = [0] * 16
        for i in range(4):
            for j in range(4):
                roundKey[j*4+i] = expandedKey[roundKeyPointer + i*4 + j]
        return roundKey

    def galois_multiplication(self, a, b):
        """Galois multiplication of 8 bit characters a and b."""
        p = 0
        for counter in range(8):
            if b & 1: p ^= a
            hi_bit_set = a & 0x80
            a <<= 1
            # keep a 8 bit
            a &= 0xFF
            if hi_bit_set:
                a ^= 0x1b
            b >>= 1
        return p

    #
    # substitute all the values from the state with the value in the SBox
    # using the state value as index for the SBox
    #
    def subBytes(self, state, isInv):
        if isInv: getter = self.getSBoxInvert
        else: getter = self.getSBoxValue
        for i in range(16): state[i] = getter(state[i])
        return state

    # iterate over the 4 rows and call shiftRow() with that row
    def shiftRows(self, state, isInv):
        for i in range(4):
            state = self.shiftRow(state, i*4, i, isInv)
        return state

    # each iteration shifts the row to the left by 1
    def shiftRow(self, state, statePointer, nbr, isInv):
        for i in range(nbr):
            if isInv:
                state[statePointer:statePointer+4] = \
                        state[statePointer+3:statePointer+4] + \
                        state[statePointer:statePointer+3]
            else:
                state[statePointer:statePointer+4] = \
                        state[statePointer+1:statePointer+4] + \
                        state[statePointer:statePointer+1]
        return state

    # galois multiplication of the 4x4 matrix
    def mixColumns(self, state, isInv):
        # iterate over the 4 columns
        for i in range(4):
            # construct one column by slicing over the 4 rows
            column = state[i:i+16:4]
            # apply the mixColumn on one column
            column = self.mixColumn(column, isInv)
            # put the values back into the state
            state[i:i+16:4] = column

        return state

    # galois multiplication of 1 column of the 4x4 matrix
    def mixColumn(self, column, isInv):
        if isInv: mult = [14, 9, 13, 11]
        else: mult = [2, 1, 1, 3]
        cpy = list(column)
        g = self.galois_multiplication

        column[0] = g(cpy[0], mult[0]) ^ g(cpy[3], mult[1]) ^ \
                    g(cpy[2], mult[2]) ^ g(cpy[1], mult[3])
        column[1] = g(cpy[1], mult[0]) ^ g(cpy[0], mult[1]) ^ \
                    g(cpy[3], mult[2]) ^ g(cpy[2], mult[3])
        column[2] = g(cpy[2], mult[0]) ^ g(cpy[1], mult[1]) ^ \
                    g(cpy[0], mult[2]) ^ g(cpy[3], mult[3])
        column[3] = g(cpy[3], mult[0]) ^ g(cpy[2], mult[1]) ^ \
                    g(cpy[1], mult[2]) ^ g(cpy[0], mult[3])
        return column

    # applies the 4 operations of the forward round in sequence
    def aes_round(self, state, roundKey):
        state = self.subBytes(state, False)
        state = self.shiftRows(state, False)
        state = self.mixColumns(state, False)
        state = self.addRoundKey(state, roundKey)
        return state

    # applies the 4 operations of the inverse round in sequence
    def aes_invRound(self, state, roundKey):
        state = self.shiftRows(state, True)
        state = self.subBytes(state, True)
        state = self.addRoundKey(state, roundKey)
        state = self.mixColumns(state, True)
        return state

    # Perform the initial operations, the standard round, and the final
    # operations of the forward aes, creating a round key for each round
    def aes_main(self, state, expandedKey, nbrRounds):
        state = self.addRoundKey(state, self.createRoundKey(expandedKey, 0))
        i = 1
        while i < nbrRounds:
            state = self.aes_round(state,
                                   self.createRoundKey(expandedKey, 16*i))
            i += 1
        state = self.subBytes(state, False)
        state = self.shiftRows(state, False)
        state = self.addRoundKey(state,
                                 self.createRoundKey(expandedKey, 16*nbrRounds))
        return state

    # Perform the initial operations, the standard round, and the final
    # operations of the inverse aes, creating a round key for each round
    def aes_invMain(self, state, expandedKey, nbrRounds):
        state = self.addRoundKey(state,
                                 self.createRoundKey(expandedKey, 16*nbrRounds))
        i = nbrRounds - 1
        while i > 0:
            state = self.aes_invRound(state,
                                      self.createRoundKey(expandedKey, 16*i))
            i -= 1
        state = self.shiftRows(state, True)
        state = self.subBytes(state, True)
        state = self.addRoundKey(state, self.createRoundKey(expandedKey, 0))
        return state

    # encrypts a 128 bit input block against the given key of size specified
    def encrypt(self, iput, key, size):
        output = [0] * 16
        # the number of rounds
        nbrRounds = 0
        # the 128 bit block to encode
        block = [0] * 16
        # set the number of rounds
        if size == self.keySize["SIZE_128"]: nbrRounds = 10
        elif size == self.keySize["SIZE_192"]: nbrRounds = 12
        elif size == self.keySize["SIZE_256"]: nbrRounds = 14
        else: return None

        # the expanded keySize
        expandedKeySize = 16*(nbrRounds+1)

        # Set the block values, for the block:
        # a0,0 a0,1 a0,2 a0,3
        # a1,0 a1,1 a1,2 a1,3
        # a2,0 a2,1 a2,2 a2,3
        # a3,0 a3,1 a3,2 a3,3
        # the mapping order is a0,0 a1,0 a2,0 a3,0 a0,1 a1,1 ... a2,3 a3,3
        #
        # iterate over the columns
        for i in range(4):
            # iterate over the rows
            for j in range(4):
                block[(i+(j*4))] = iput[(i*4)+j]

        # expand the key into an 176, 208, 240 bytes key
        # the expanded key
        expandedKey = self.expandKey(key, size, expandedKeySize)

        # encrypt the block using the expandedKey
        block = self.aes_main(block, expandedKey, nbrRounds)

        # unmap the block again into the output
        for k in range(4):
            # iterate over the rows
            for l in range(4):
                output[(k*4)+l] = block[(k+(l*4))]
        return output

    # decrypts a 128 bit input block against the given key of size specified
    def decrypt(self, iput, key, size):
        output = [0] * 16
        # the number of rounds
        nbrRounds = 0
        # the 128 bit block to decode
        block = [0] * 16
        # set the number of rounds
        if size == self.keySize["SIZE_128"]: nbrRounds = 10
        elif size == self.keySize["SIZE_192"]: nbrRounds = 12
        elif size == self.keySize["SIZE_256"]: nbrRounds = 14
        else: return None

        # the expanded keySize
        expandedKeySize = 16*(nbrRounds+1)

        # Set the block values, for the block:
        # a0,0 a0,1 a0,2 a0,3
        # a1,0 a1,1 a1,2 a1,3
        # a2,0 a2,1 a2,2 a2,3
        # a3,0 a3,1 a3,2 a3,3
        # the mapping order is a0,0 a1,0 a2,0 a3,0 a0,1 a1,1 ... a2,3 a3,3

        # iterate over the columns
        for i in range(4):
            # iterate over the rows
            for j in range(4):
                block[(i+(j*4))] = iput[(i*4)+j]
        # expand the key into an 176, 208, 240 bytes key
        expandedKey = self.expandKey(key, size, expandedKeySize)
        # decrypt the block using the expandedKey
        block = self.aes_invMain(block, expandedKey, nbrRounds)
        # unmap the block again into the output
        for k in range(4):
            # iterate over the rows
            for l in range(4):
                output[(k*4)+l] = block[(k+(l*4))]
        return output

class AESModeOfOperation(object):

    aes = AES()

    # structure of supported modes of operation
    modeOfOperation = dict(OFB=0, CFB=1, CBC=2)

    # converts a 16 character string into a number array
    def convertString(self, string, start, end, mode):
        if end - start > 16: end = start + 16
        if mode == self.modeOfOperation["CBC"]: ar = [0] * 16
        else: ar = []

        i = start
        j = 0
        while len(ar) < end - start:
            ar.append(0)
        while i < end:
            ar[j] = ord(string[i])
            j += 1
            i += 1
        return ar

    # Mode of Operation Encryption
    # stringIn - Input String
    # mode - mode of type modeOfOperation
    # hexKey - a hex key of the bit length size
    # size - the bit length of the key
    # hexIV - the 128 bit hex Initilization Vector
    def encrypt(self, stringIn, mode, key, size, IV):
        if len(key) % size:
            return None
        if len(IV) % 16:
            return None
        # the AES input/output
        plaintext = []
        iput = [0] * 16
        output = []
        ciphertext = [0] * 16
        # the output cipher string
        cipherOut = []
        # char firstRound
        firstRound = True
        if stringIn != None:
            for j in range(int(math.ceil(float(len(stringIn))/16))):
                start = j*16
                end = j*16+16
                if  end > len(stringIn):
                    end = len(stringIn)
                plaintext = self.convertString(stringIn, start, end, mode)
                # print 'PT@%s:%s' % (j, plaintext)
                if mode == self.modeOfOperation["CFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(plaintext)-1 < i:
                            ciphertext[i] = 0 ^ output[i]
                        elif len(output)-1 < i:
                            ciphertext[i] = plaintext[i] ^ 0
                        elif len(plaintext)-1 < i and len(output) < i:
                            ciphertext[i] = 0 ^ 0
                        else:
                            ciphertext[i] = plaintext[i] ^ output[i]
                    for k in range(end-start):
                        cipherOut.append(ciphertext[k])
                    iput = ciphertext
                elif mode == self.modeOfOperation["OFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(plaintext)-1 < i:
                            ciphertext[i] = 0 ^ output[i]
                        elif len(output)-1 < i:
                            ciphertext[i] = plaintext[i] ^ 0
                        elif len(plaintext)-1 < i and len(output) < i:
                            ciphertext[i] = 0 ^ 0
                        else:
                            ciphertext[i] = plaintext[i] ^ output[i]
                    for k in range(end-start):
                        cipherOut.append(ciphertext[k])
                    iput = output
                elif mode == self.modeOfOperation["CBC"]:
                    for i in range(16):
                        if firstRound:
                            iput[i] =  plaintext[i] ^ IV[i]
                        else:
                            iput[i] =  plaintext[i] ^ ciphertext[i]
                    # print 'IP@%s:%s' % (j, iput)
                    firstRound = False
                    ciphertext = self.aes.encrypt(iput, key, size)
                    # always 16 bytes because of the padding for CBC
                    for k in range(16):
                        cipherOut.append(ciphertext[k])
        return mode, len(stringIn), cipherOut

    # Mode of Operation Decryption
    # cipherIn - Encrypted String
    # originalsize - The unencrypted string length - required for CBC
    # mode - mode of type modeOfOperation
    # key - a number array of the bit length size
    # size - the bit length of the key
    # IV - the 128 bit number array Initilization Vector
    def decrypt(self, cipherIn, originalsize, mode, key, size, IV):
        # cipherIn = unescCtrlChars(cipherIn)
        if len(key) % size:
            return None
        if len(IV) % 16:
            return None
        # the AES input/output
        ciphertext = []
        iput = []
        output = []
        plaintext = [0] * 16
        # the output plain text string
        stringOut = ''
        # char firstRound
        firstRound = True
        if cipherIn != None:
            for j in range(int(math.ceil(float(len(cipherIn))/16))):
                start = j*16
                end = j*16+16
                if j*16+16 > len(cipherIn):
                    end = len(cipherIn)
                ciphertext = cipherIn[start:end]
                if mode == self.modeOfOperation["CFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(output)-1 < i:
                            plaintext[i] = 0 ^ ciphertext[i]
                        elif len(ciphertext)-1 < i:
                            plaintext[i] = output[i] ^ 0
                        elif len(output)-1 < i and len(ciphertext) < i:
                            plaintext[i] = 0 ^ 0
                        else:
                            plaintext[i] = output[i] ^ ciphertext[i]
                    for k in range(end-start):
                        stringOut += chr(plaintext[k])
                    iput = ciphertext
                elif mode == self.modeOfOperation["OFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(output)-1 < i:
                            plaintext[i] = 0 ^ ciphertext[i]
                        elif len(ciphertext)-1 < i:
                            plaintext[i] = output[i] ^ 0
                        elif len(output)-1 < i and len(ciphertext) < i:
                            plaintext[i] = 0 ^ 0
                        else:
                            plaintext[i] = output[i] ^ ciphertext[i]
                    for k in range(end-start):
                        stringOut += chr(plaintext[k])
                    iput = output
                elif mode == self.modeOfOperation["CBC"]:
                    output = self.aes.decrypt(ciphertext, key, size)
                    for i in range(16):
                        if firstRound:
                            plaintext[i] = IV[i] ^ output[i]
                        else:
                            plaintext[i] = iput[i] ^ output[i]
                    firstRound = False
                    if originalsize is not None and originalsize < end:
                        for k in range(originalsize-start):
                            stringOut += chr(plaintext[k])
                    else:
                        for k in range(end-start):
                            stringOut += chr(plaintext[k])
                    iput = ciphertext
        return stringOut

# end of aes.py code

# pywallet crypter implementation

crypter = None

try:
    from Crypto.Cipher import AES
    crypter = 'pycrypto'
except:
    pass

class Crypter_pycrypto( object ):
    def SetKeyFromPassphrase(self, vKeyData, vSalt, nDerivIterations, nDerivationMethod):
        if nDerivationMethod != 0:
            return 0
        data = vKeyData + vSalt
        for i in xrange(nDerivIterations):
            data = hashlib.sha512(data).digest()
        self.SetKey(data[0:32])
        self.SetIV(data[32:32+16])
        return len(data)

    def SetKey(self, key):
        self.chKey = key

    def SetIV(self, iv):
        self.chIV = iv[0:16]

    def Encrypt(self, data):
        return AES.new(self.chKey,AES.MODE_CBC,self.chIV).encrypt(data)[0:32]
 
    def Decrypt(self, data):
        return AES.new(self.chKey,AES.MODE_CBC,self.chIV).decrypt(data)[0:32]

try:
    if not crypter:
        import ctypes
        import ctypes.util
        ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl') or 'libeay32')
        crypter = 'ssl'
except:
    pass

class Crypter_ssl(object):
    def __init__(self):
        self.chKey = ctypes.create_string_buffer (32)
        self.chIV = ctypes.create_string_buffer (16)

    def SetKeyFromPassphrase(self, vKeyData, vSalt, nDerivIterations, nDerivationMethod):
        if nDerivationMethod != 0:
            return 0
        strKeyData = ctypes.create_string_buffer (vKeyData)
        chSalt = ctypes.create_string_buffer (vSalt)
        return ssl.EVP_BytesToKey(ssl.EVP_aes_256_cbc(), ssl.EVP_sha512(), chSalt, strKeyData,
            len(vKeyData), nDerivIterations, ctypes.byref(self.chKey), ctypes.byref(self.chIV))

    def SetKey(self, key):
        self.chKey = ctypes.create_string_buffer(key)

    def SetIV(self, iv):
        self.chIV = ctypes.create_string_buffer(iv)

    def Encrypt(self, data):
        buf = ctypes.create_string_buffer(len(data) + 16)
        written = ctypes.c_int(0)
        final = ctypes.c_int(0)
        ctx = ssl.EVP_CIPHER_CTX_new()
        ssl.EVP_CIPHER_CTX_init(ctx)
        ssl.EVP_EncryptInit_ex(ctx, ssl.EVP_aes_256_cbc(), None, self.chKey, self.chIV)
        ssl.EVP_EncryptUpdate(ctx, buf, ctypes.byref(written), data, len(data))
        output = buf.raw[:written.value]
        ssl.EVP_EncryptFinal_ex(ctx, buf, ctypes.byref(final))
        output += buf.raw[:final.value]
        return output

    def Decrypt(self, data):
        buf = ctypes.create_string_buffer(len(data) + 16)
        written = ctypes.c_int(0)
        final = ctypes.c_int(0)
        ctx = ssl.EVP_CIPHER_CTX_new()
        ssl.EVP_CIPHER_CTX_init(ctx)
        ssl.EVP_DecryptInit_ex(ctx, ssl.EVP_aes_256_cbc(), None, self.chKey, self.chIV)
        ssl.EVP_DecryptUpdate(ctx, buf, ctypes.byref(written), data, len(data))
        output = buf.raw[:written.value]
        ssl.EVP_DecryptFinal_ex(ctx, buf, ctypes.byref(final))
        output += buf.raw[:final.value]
        return output

class Crypter_pure(object):
    def __init__(self):
        self.m = AESModeOfOperation()
        self.cbc = self.m.modeOfOperation["CBC"]
        self.sz = self.m.aes.keySize["SIZE_256"]

    def SetKeyFromPassphrase(self, vKeyData, vSalt, nDerivIterations, nDerivationMethod):
        if nDerivationMethod != 0:
            return 0
        data = vKeyData + vSalt
        for i in xrange(nDerivIterations):
            data = hashlib.sha512(data).digest()
        self.SetKey(data[0:32])
        self.SetIV(data[32:32+16])
        return len(data)

    def SetKey(self, key):
        self.chKey = [ord(i) for i in key]

    def SetIV(self, iv):
        self.chIV = [ord(i) for i in iv]

    def Encrypt(self, data):
        mode, size, cypher = self.m.encrypt(data, self.cbc, self.chKey, self.sz, self.chIV)
        return ''.join(map(chr, cypher))
 
    def Decrypt(self, data):
        chData = [ord(i) for i in data]
        return self.m.decrypt(chData, self.sz, self.cbc, self.chKey, self.sz, self.chIV)

# secp256k1

_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L

# python-ecdsa code (EC_KEY implementation)

class CurveFp( object ):
    def __init__( self, p, a, b ):
        self.__p = p
        self.__a = a
        self.__b = b

    def p( self ):
        return self.__p

    def a( self ):
        return self.__a

    def b( self ):
        return self.__b

    def contains_point( self, x, y ):
        return ( y * y - ( x * x * x + self.__a * x + self.__b ) ) % self.__p == 0

class Point( object ):
    def __init__( self, curve, x, y, order = None ):
        self.__curve = curve
        self.__x = x
        self.__y = y
        self.__order = order
        if self.__curve: assert self.__curve.contains_point( x, y )
        if order: assert self * order == INFINITY
 
    def __add__( self, other ):
        if other == INFINITY: return self
        if self == INFINITY: return other
        assert self.__curve == other.__curve
        if self.__x == other.__x:
            if ( self.__y + other.__y ) % self.__curve.p() == 0:
                return INFINITY
            else:
                return self.double()

        p = self.__curve.p()
        l = ( ( other.__y - self.__y ) * \
                    inverse_mod( other.__x - self.__x, p ) ) % p
        x3 = ( l * l - self.__x - other.__x ) % p
        y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
        return Point( self.__curve, x3, y3 )

    def __mul__( self, other ):
        def leftmost_bit( x ):
            assert x > 0
            result = 1L
            while result <= x: result = 2 * result
            return result / 2

        e = other
        if self.__order: e = e % self.__order
        if e == 0: return INFINITY
        if self == INFINITY: return INFINITY
        assert e > 0
        e3 = 3 * e
        negative_self = Point( self.__curve, self.__x, -self.__y, self.__order )
        i = leftmost_bit( e3 ) / 2
        result = self
        while i > 1:
            result = result.double()
            if ( e3 & i ) != 0 and ( e & i ) == 0: result = result + self
            if ( e3 & i ) == 0 and ( e & i ) != 0: result = result + negative_self
            i = i / 2
        return result

    def __rmul__( self, other ):
        return self * other

    def __str__( self ):
        if self == INFINITY: return "infinity"
        return "(%d,%d)" % ( self.__x, self.__y )

    def double( self ):
        if self == INFINITY:
            return INFINITY

        p = self.__curve.p()
        a = self.__curve.a()
        l = ( ( 3 * self.__x * self.__x + a ) * \
                    inverse_mod( 2 * self.__y, p ) ) % p
        x3 = ( l * l - 2 * self.__x ) % p
        y3 = ( l * ( self.__x - x3 ) - self.__y ) % p
        return Point( self.__curve, x3, y3 )

    def x( self ):
        return self.__x

    def y( self ):
        return self.__y

    def curve( self ):
        return self.__curve
    
    def order( self ):
        return self.__order
        
INFINITY = Point( None, None, None )

def inverse_mod( a, m ):
    if a < 0 or m <= a: a = a % m
    c, d = a, m
    uc, vc, ud, vd = 1, 0, 0, 1
    while c != 0:
        q, c, d = divmod( d, c ) + ( c, )
        uc, vc, ud, vd = ud - q*uc, vd - q*vc, uc, vc
    assert d == 1
    if ud > 0: return ud
    else: return ud + m

class Signature( object ):
    def __init__( self, r, s ):
        self.r = r
        self.s = s
        
class Public_key( object ):
    def __init__( self, generator, point ):
        self.curve = generator.curve()
        self.generator = generator
        self.point = point
        n = generator.order()
        if not n:
            raise RuntimeError, "Generator point must have order."
        if not n * point == INFINITY:
            raise RuntimeError, "Generator point order is bad."
        if point.x() < 0 or n <= point.x() or point.y() < 0 or n <= point.y():
            raise RuntimeError, "Generator point has x or y out of range."

    def verifies( self, hash, signature ):
        G = self.generator
        n = G.order()
        r = signature.r
        s = signature.s
        if r < 1 or r > n-1: return False
        if s < 1 or s > n-1: return False
        c = inverse_mod( s, n )
        u1 = ( hash * c ) % n
        u2 = ( r * c ) % n
        xy = u1 * G + u2 * self.point
        v = xy.x() % n
        return v == r

class Private_key( object ):
    def __init__( self, public_key, secret_multiplier ):
        self.public_key = public_key
        self.secret_multiplier = secret_multiplier

    def der( self ):
        hex_der_key = '06052b8104000a30740201010420' + \
            '%064x' % self.secret_multiplier + \
            'a00706052b8104000aa14403420004' + \
            '%064x' % self.public_key.point.x() + \
            '%064x' % self.public_key.point.y()
        return hex_der_key.decode('hex')

    def sign( self, hash, random_k ):
        G = self.public_key.generator
        n = G.order()
        k = random_k % n
        p1 = k * G
        r = p1.x()
        if r == 0: raise RuntimeError, "amazingly unlucky random number r"
        s = ( inverse_mod( k, n ) * \
                    ( hash + ( self.secret_multiplier * r ) % n ) ) % n
        if s == 0: raise RuntimeError, "amazingly unlucky random number s"
        return Signature( r, s )

class EC_KEY(object):
    def __init__( self, secret ):
        curve = CurveFp( _p, _a, _b )
        generator = Point( curve, _Gx, _Gy, _r )
        self.pubkey = Public_key( generator, generator * secret )
        self.privkey = Private_key( self.pubkey, secret )
        self.secret = secret

# end of python-ecdsa code

# pywallet openssl private key implementation

def i2d_ECPrivateKey(pkey, compressed=False):
    if compressed:
        key = '3081d30201010420' + \
            '%064x' % pkey.secret + \
            'a081a53081a2020101302c06072a8648ce3d0101022100' + \
            '%064x' % _p + \
            '3006040100040107042102' + \
            '%064x' % _Gx + \
            '022100' + \
            '%064x' % _r + \
            '020101a124032200'
    else:
        key = '308201130201010420' + \
            '%064x' % pkey.secret + \
            'a081a53081a2020101302c06072a8648ce3d0101022100' + \
            '%064x' % _p + \
            '3006040100040107044104' + \
            '%064x' % _Gx + \
            '%064x' % _Gy + \
            '022100' + \
            '%064x' % _r + \
            '020101a144034200'

    return key.decode('hex') + i2o_ECPublicKey(pkey, compressed)

def i2o_ECPublicKey(pkey, compressed=False):
    # public keys are 65 bytes long (520 bits)
    # 0x04 + 32-byte X-coordinate + 32-byte Y-coordinate
    # 0x00 = point at infinity, 0x02 and 0x03 = compressed, 0x04 = uncompressed
    # compressed keys: <sign> <x> where <sign> is 0x02 if y is even and 0x03 if y is odd
    if compressed:
        if pkey.pubkey.point.y() & 1:
            key = '03' + '%064x' % pkey.pubkey.point.x()
        else:
            key = '02' + '%064x' % pkey.pubkey.point.x()
    else:
        key = '04' + \
            '%064x' % pkey.pubkey.point.x() + \
            '%064x' % pkey.pubkey.point.y()

    return key.decode('hex')

# bitcointools hashes and base58 implementation

def hash_160(public_key):
    md = hashlib.new('ripemd160')
    md.update(hashlib.sha256(public_key).digest())
    return md.digest()

def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)

def hash_160_to_bc_address(h160):
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)

def bc_address_to_hash_160(addr):
    bytes = b58decode(addr, 25)
    return bytes[1:21]

__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
    """ encode v, which is a string of bytes, to base58.        
    """

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break

    return (__b58chars[0]*nPad) + result

def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result

# end of bitcointools base58 implementation


# address handling code

def Hash(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def EncodeBase58Check(secret):
    hash = Hash(secret)
    return b58encode(secret + hash[0:4])

def DecodeBase58Check(sec):
    vchRet = b58decode(sec, None)
    secret = vchRet[0:-4]
    csum = vchRet[-4:]
    hash = Hash(secret)
    cs32 = hash[0:4]
    if cs32 != csum:
        return None
    else:
        return secret

def PrivKeyToSecret(privkey):
    if len(privkey) == 279:
        return privkey[9:9+32]
    else:
        return privkey[8:8+32]

def SecretToASecret(secret, compressed=False):
    vchIn = chr((addrtype+128)&255) + secret
    if compressed: vchIn += '\01'
    return EncodeBase58Check(vchIn)

def ASecretToSecret(sec):
    vch = DecodeBase58Check(sec)
    if vch and vch[0] == chr((addrtype+128)&255):
        return vch[1:]
    else:
        return False

def regenerate_key(sec):
    b = ASecretToSecret(sec)
    if not b:
        return False
    b = b[0:32]
    secret = int('0x' + b.encode('hex'), 16)
    return EC_KEY(secret)

def GetPubKey(pkey, compressed=False):
    return i2o_ECPublicKey(pkey, compressed)

def GetPrivKey(pkey, compressed=False):
    return i2d_ECPrivateKey(pkey, compressed)

def GetSecret(pkey):
    return ('%064x' % pkey.secret).decode('hex')

def is_compressed(sec):
    b = ASecretToSecret(sec)
    return len(b) == 33

# bitcointools wallet.dat handling code

def create_env(db_dir):
    db_env = DBEnv(0)
    r = db_env.open(db_dir, (DB_CREATE|DB_INIT_LOCK|DB_INIT_LOG|DB_INIT_MPOOL|DB_INIT_TXN|DB_THREAD|DB_RECOVER))
    return db_env

def parse_CAddress(vds):
    d = {'ip':'0.0.0.0','port':0,'nTime': 0}
    try:
        d['nVersion'] = vds.read_int32()
        d['nTime'] = vds.read_uint32()
        d['nServices'] = vds.read_uint64()
        d['pchReserved'] = vds.read_bytes(12)
        d['ip'] = socket.inet_ntoa(vds.read_bytes(4))
        d['port'] = vds.read_uint16()
    except:
        pass
    return d

def deserialize_CAddress(d):
    return d['ip']+":"+str(d['port'])

def parse_BlockLocator(vds):
    d = { 'hashes' : [] }
    nHashes = vds.read_compact_size()
    for i in xrange(nHashes):
        d['hashes'].append(vds.read_bytes(32))
        return d

def deserialize_BlockLocator(d):
  result = "Block Locator top: "+d['hashes'][0][::-1].encode('hex_codec')
  return result

def parse_setting(setting, vds):
    if setting[0] == "f":    # flag (boolean) settings
        return str(vds.read_boolean())
    elif setting[0:4] == "addr": # CAddress
        d = parse_CAddress(vds)
        return deserialize_CAddress(d)
    elif setting == "nTransactionFee":
        return vds.read_int64()
    elif setting == "nLimitProcessors":
        return vds.read_int32()
    return 'unknown setting'

class SerializationError(Exception):
    """ Thrown when there's a problem deserializing or serializing """

class BCDataStream(object):
    def __init__(self):
        self.input = None
        self.read_cursor = 0

    def clear(self):
        self.input = None
        self.read_cursor = 0

    def write(self, bytes):    # Initialize with string of bytes
        if self.input is None:
            self.input = bytes
        else:
            self.input += bytes

    def map_file(self, file, start):    # Initialize with bytes from file
        self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        self.read_cursor = start
    def seek_file(self, position):
        self.read_cursor = position
    def close_file(self):
        self.input.close()

    def read_string(self):
        # Strings are encoded depending on length:
        # 0 to 252 :    1-byte-length followed by bytes (if any)
        # 253 to 65,535 : byte'253' 2-byte-length followed by bytes
        # 65,536 to 4,294,967,295 : byte '254' 4-byte-length followed by bytes
        # ... and the Bitcoin client is coded to understand:
        # greater than 4,294,967,295 : byte '255' 8-byte-length followed by bytes of string
        # ... but I don't think it actually handles any strings that big.
        if self.input is None:
            raise SerializationError("call write(bytes) before trying to deserialize")

        try:
            length = self.read_compact_size()
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return self.read_bytes(length)

    def write_string(self, string):
        # Length-encoded as with read-string
        self.write_compact_size(len(string))
        self.write(string)

    def read_bytes(self, length):
        try:
            result = self.input[self.read_cursor:self.read_cursor+length]
            self.read_cursor += length
            return result
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return ''

    def read_boolean(self): return self.read_bytes(1)[0] != chr(0)
    def read_int16(self): return self._read_num('<h')
    def read_uint16(self): return self._read_num('<H')
    def read_int32(self): return self._read_num('<i')
    def read_uint32(self): return self._read_num('<I')
    def read_int64(self): return self._read_num('<q')
    def read_uint64(self): return self._read_num('<Q')

    def write_boolean(self, val): return self.write(chr(1) if val else chr(0))
    def write_int16(self, val): return self._write_num('<h', val)
    def write_uint16(self, val): return self._write_num('<H', val)
    def write_int32(self, val): return self._write_num('<i', val)
    def write_uint32(self, val): return self._write_num('<I', val)
    def write_int64(self, val): return self._write_num('<q', val)
    def write_uint64(self, val): return self._write_num('<Q', val)

    def read_compact_size(self):
        size = ord(self.input[self.read_cursor])
        self.read_cursor += 1
        if size == 253:
            size = self._read_num('<H')
        elif size == 254:
            size = self._read_num('<I')
        elif size == 255:
            size = self._read_num('<Q')
        return size

    def write_compact_size(self, size):
        if size < 0:
            raise SerializationError("attempt to write size < 0")
        elif size < 253:
             self.write(chr(size))
        elif size < 2**16:
            self.write('\xfd')
            self._write_num('<H', size)
        elif size < 2**32:
            self.write('\xfe')
            self._write_num('<I', size)
        elif size < 2**64:
            self.write('\xff')
            self._write_num('<Q', size)

    def _read_num(self, format):
        (i,) = struct.unpack_from(format, self.input, self.read_cursor)
        self.read_cursor += struct.calcsize(format)
        return i

    def _write_num(self, format, num):
        s = struct.pack(format, num)
        self.write(s)

def open_wallet(db_env, writable=False):
    db = DB(db_env)
    flags = DB_THREAD | (DB_CREATE if writable else DB_RDONLY)
    try:
        r = db.open("wallet.dat", "main", DB_BTREE, flags)
    except DBError:
        r = True

    if r is not None:
        logging.error("Couldn't open wallet.dat/main. Try quitting Bitcoin and running this again.")
        sys.exit(1)
    
    return db

def parse_wallet(db, item_callback):
    kds = BCDataStream()
    vds = BCDataStream()

    for (key, value) in db.items():
        d = { }

        kds.clear(); kds.write(key)
        vds.clear(); vds.write(value)

        type = kds.read_string()

        d["__key__"] = key
        d["__value__"] = value
        d["__type__"] = type

        try:
            if type == "tx":
                d["tx_id"] = kds.read_bytes(32)
            elif type == "name":
                d['hash'] = kds.read_string()
                d['name'] = vds.read_string()
            elif type == "version":
                d['version'] = vds.read_uint32()
            elif type == "minversion":
                d['minversion'] = vds.read_uint32()
            elif type == "setting":
                d['setting'] = kds.read_string()
                d['value'] = parse_setting(d['setting'], vds)
            elif type == "key":
                d['public_key'] = kds.read_bytes(kds.read_compact_size())
                d['private_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "wkey":
                d['public_key'] = kds.read_bytes(kds.read_compact_size())
                d['private_key'] = vds.read_bytes(vds.read_compact_size())
                d['created'] = vds.read_int64()
                d['expires'] = vds.read_int64()
                d['comment'] = vds.read_string()
            elif type == "ckey":
                d['public_key'] = kds.read_bytes(kds.read_compact_size())
                d['crypted_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "mkey":
                d['nID'] = kds.read_int32()
                d['crypted_key'] = vds.read_bytes(vds.read_compact_size())
                d['salt'] = vds.read_bytes(vds.read_compact_size())
                d['nDerivationMethod'] = vds.read_int32()
                d['nDeriveIterations'] = vds.read_int32()
                d['vchOtherDerivationParameters'] = vds.read_bytes(vds.read_compact_size())
            elif type == "defaultkey":
                d['key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "pool":
                d['n'] = kds.read_int64()
                d['nVersion'] = vds.read_int32()
                d['nTime'] = vds.read_int64()
                d['public_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "acc":
                d['account'] = kds.read_string()
                d['nVersion'] = vds.read_int32()
                d['public_key'] = vds.read_bytes(vds.read_compact_size())
            elif type == "acentry":
                d['account'] = kds.read_string()
                d['n'] = kds.read_uint64()
                d['nVersion'] = vds.read_int32()
                d['nCreditDebit'] = vds.read_int64()
                d['nTime'] = vds.read_int64()
                d['otherAccount'] = vds.read_string()
                d['comment'] = vds.read_string()
            elif type == "bestblock":
                d['nVersion'] = vds.read_int32()
                d.update(parse_BlockLocator(vds))
            
            item_callback(type, d)

        except Exception, e:
            traceback.print_exc()
            print("ERROR parsing wallet.dat, type %s" % type)
            print("key data in hex: %s"%key.encode('hex_codec'))
            print("value data in hex: %s"%value.encode('hex_codec'))
            sys.exit(1)
    
def update_wallet(db, type, data):
    """Write a single item to the wallet.
    db must be open with writable=True.
    type and data are the type code and data dictionary as parse_wallet would
    give to item_callback.
    data's __key__, __value__ and __type__ are ignored; only the primary data
    fields are used.
    """
    d = data
    kds = BCDataStream()
    vds = BCDataStream()

    # Write the type code to the key
    kds.write_string(type)
    vds.write("")                         # Ensure there is something

    try:
        if type == "tx":
            raise NotImplementedError("Writing items of type 'tx'")
            kds.write(d['tx_id'])
        elif type == "name":
            kds.write_string(d['hash'])
            vds.write_string(d['name'])
        elif type == "version":
            vds.write_uint32(d['version'])
        elif type == "minversion":
            vds.write_uint32(d['minversion'])
        elif type == "setting":
            raise NotImplementedError("Writing items of type 'setting'")
            kds.write_string(d['setting'])
            #d['value'] = parse_setting(d['setting'], vds)
        elif type == "key":
            kds.write_string(d['public_key'])
            vds.write_string(d['private_key'])
        elif type == "wkey":
            kds.write_string(d['public_key'])
            vds.write_string(d['private_key'])
            vds.write_int64(d['created'])
            vds.write_int64(d['expires'])
            vds.write_string(d['comment'])
        elif type == "ckey":
            kds.write_string(d['public_key'])
            vds.write_string(d['crypted_key'])
        elif type == "defaultkey":
            vds.write_string(d['key'])
        elif type == "pool":
            kds.write_int64(d['n'])
            vds.write_int32(d['nVersion'])
            vds.write_int64(d['nTime'])
            vds.write_string(d['public_key'])
        elif type == "acc":
            kds.write_string(d['account'])
            vds.write_int32(d['nVersion'])
            vds.write_string(d['public_key'])
        elif type == "acentry":
            kds.write_string(d['account'])
            kds.write_uint64(d['n'])
            vds.write_int32(d['nVersion'])
            vds.write_int64(d['nCreditDebit'])
            vds.write_int64(d['nTime'])
            vds.write_string(d['otherAccount'])
            vds.write_string(d['comment'])
        elif type == "bestblock":
            vds.write_int32(d['nVersion'])
            vds.write_compact_size(len(d['hashes']))
            for h in d['hashes']:
                vds.write(h)
        else:
            print "Unknown key type: "+type

        # Write the key/value pair to the database
        db.put(kds.input, vds.input)

    except Exception, e:
        print("ERROR writing to wallet.dat, type %s"%type)
        print("data dictionary: %r"%data)
        traceback.print_exc()

def rewrite_wallet(db_env, destFileName, pre_put_callback=None):
    db = open_wallet(db_env)

    db_out = DB(db_env)
    try:
        r = db_out.open(destFileName, "main", DB_BTREE, DB_CREATE)
    except DBError:
        r = True

    if r is not None:
        logging.error("Couldn't open %s."%destFileName)
        sys.exit(1)

    def item_callback(type, d):
        if (pre_put_callback is None or pre_put_callback(type, d)):
            db_out.put(d["__key__"], d["__value__"])

    parse_wallet(db, item_callback)
    db_out.close()
    db.close()

# end of bitcointools wallet.dat handling code

# wallet.dat reader / writer

def read_wallet(json_db, db_env, print_wallet, print_wallet_transactions, transaction_filter):
    global password

    db = open_wallet(db_env)

    json_db['keys'] = []
    json_db['pool'] = []
    json_db['names'] = {}

    def item_callback(type, d):

        if type == "name":
            json_db['names'][d['hash']] = d['name']

        elif type == "version":
            json_db['version'] = d['version']

        elif type == "minversion":
            json_db['minversion'] = d['minversion']

        elif type == "setting":
            if not json_db.has_key('settings'): json_db['settings'] = {}
            json_db["settings"][d['setting']] = d['value']

        elif type == "defaultkey":
            json_db['defaultkey'] = public_key_to_bc_address(d['key'])

        elif type == "key":
            addr = public_key_to_bc_address(d['public_key'])
            compressed = d['public_key'][0] != '\04'
            sec = SecretToASecret(PrivKeyToSecret(d['private_key']), compressed)
            private_keys.append(sec)
            json_db['keys'].append({'addr' : addr, 'sec' : sec})
#            json_db['keys'].append({'addr' : addr, 'sec' : sec, 
#                'secret':PrivKeyToSecret(d['private_key']).encode('hex'),
#                'pubkey':d['public_key'].encode('hex'), 
#                'privkey':d['private_key'].encode('hex')})

        elif type == "wkey":
            if not json_db.has_key('wkey'): json_db['wkey'] = []
            json_db['wkey']['created'] = d['created']

        elif type == "ckey":
            addr = public_key_to_bc_address(d['public_key'])
            ckey = d['crypted_key']
            pubkey = d['public_key']
            json_db['keys'].append( {'addr' : addr, 'ckey': ckey.encode('hex'), 'pubkey': pubkey.encode('hex') })

        elif type == "mkey":
            mkey = {}
            mkey['nID'] = d['nID']
            mkey['crypted_key'] = d['crypted_key'].encode('hex')
            mkey['salt'] = d['salt'].encode('hex')
            mkey['nDeriveIterations'] = d['nDeriveIterations']
            mkey['nDerivationMethod'] = d['nDerivationMethod']
            mkey['vchOtherDerivationParameters'] = d['vchOtherDerivationParameters'].encode('hex')
            json_db['mkey'] = mkey

            if password:
                global crypter
                if crypter == 'pycrypto':
                    crypter = Crypter_pycrypto()
                elif crypter == 'ssl':
                    crypter = Crypter_ssl()
                else:
                    crypter = Crypter_pure()
                    logging.warning("pycrypto or libssl not found, decryption may be slow")
                res = crypter.SetKeyFromPassphrase(password, d['salt'], d['nDeriveIterations'], d['nDerivationMethod'])
                if res == 0:
                    logging.error("Unsupported derivation method")
                    sys.exit(1)
                masterkey = crypter.Decrypt(d['crypted_key'])
                crypter.SetKey(masterkey)

        elif type == "pool":
            json_db['pool'].append( {'n': d['n'], 'addr': public_key_to_bc_address(d['public_key']), 'nTime' : d['nTime'] } )

        elif type == "acc":
            json_db['acc'] = d['account']
            print("Account %s (current key: %s)"%(d['account'], public_key_to_bc_address(d['public_key'])))

        elif type == "acentry":
            json_db['acentry'] = (d['account'], d['nCreditDebit'], d['otherAccount'], time.ctime(d['nTime']), d['n'], d['comment'])

        elif type == "bestblock":
            json_db['bestblock'] = d['hashes'][0][::-1].encode('hex_codec')

        else:
            json_db[type] = 'unsupported'

    parse_wallet(db, item_callback)

    db.close()

    for k in json_db['keys']:
        addr = k['addr']
        if addr in json_db['names'].keys():
            k["label"] = json_db['names'][addr]
        else:
            k["reserve"] = 1

    crypted = 'mkey' in json_db.keys()

    if crypted and not password:
        logging.warning("encrypted wallet, specify password to decrypt")

    if crypted and password:
        check = True
        for k in json_db['keys']:
            ckey = k['ckey'].decode('hex')
            public_key = k['pubkey'].decode('hex')
            crypter.SetIV(Hash(public_key))
            secret = crypter.Decrypt(ckey)
            compressed = public_key[0] != '\04'

            if check:
                check = False
                pkey = EC_KEY(int('0x' + secret.encode('hex'), 16))
                if public_key != GetPubKey(pkey, compressed):
                    logging.error("wrong password")
                    sys.exit(1)

            sec = SecretToASecret(secret, compressed)
            k['sec'] = sec
            k['secret'] = secret.encode('hex')
            del(k['ckey'])
            del(k['secret'])
            del(k['pubkey'])
            private_keys.append(sec)

    del(json_db['pool'])
    del(json_db['names'])

def importprivkey(db, sec):

    pkey = regenerate_key(sec)
    if not pkey:
        return False

    compressed = is_compressed(sec)

    secret = GetSecret(pkey)
    private_key = GetPrivKey(pkey, compressed)
    public_key = GetPubKey(pkey, compressed)
    addr = public_key_to_bc_address(public_key)

    print "Address: %s" % addr
    print "Privkey: %s" % SecretToASecret(secret, compressed)

    global crypter, password, json_db

    crypted = 'mkey' in json_db.keys()

    if crypted:
        if password:
            crypter.SetIV(Hash(public_key))
            crypted_key = crypter.Encrypt(secret)
            update_wallet(db, 'ckey', { 'public_key' : public_key, 'crypted_key' : crypted_key })
            update_wallet(db, 'name', { 'hash' : addr, 'name' : '' })
            return True
        else:
            logging.error("password not specified")
            sys.exit(1)
    else:
        update_wallet(db, 'key', { 'public_key' : public_key, 'private_key' : private_key })
        update_wallet(db, 'name', { 'hash' : addr, 'name' : '' })
        return True

    return False

def privkey2address(sec):
    print "trying import", sec
    pkey = regenerate_key(sec)
    print pkey
    if not pkey:
        return None

    compressed = is_compressed(sec)

    public_key = GetPubKey(pkey, compressed)
    return public_key_to_bc_address(public_key)

from optparse import OptionParser

def main():

    global max_version, addrtype

    parser = OptionParser(usage="%prog [options]", version="%prog 1.2")

    parser.add_option("--dumpwallet", dest="dump", action="store_true",
        help="dump wallet in json format")

    parser.add_option("--importprivkey", dest="key",
        help="import private key from vanitygen")

    parser.add_option("--datadir", dest="datadir", 
        help="wallet directory (defaults to bitcoin default)")

    parser.add_option("--testnet", dest="testnet", action="store_true",
        help="use testnet subdirectory and address type")

    parser.add_option("--password", dest="password",
        help="password for the encrypted wallet")

    (options, args) = parser.parse_args()

    if options.dump is None and options.key is None:
        print "A mandatory option is missing\n"
        parser.print_help()
        sys.exit(1)

    if options.datadir is None:
        db_dir = determine_db_dir()
    else:
        db_dir = options.datadir

    if options.testnet:
        db_dir += "/testnet"
        addrtype = 111

    db_env = create_env(db_dir)

    global password

    if options.password:
        password = options.password

    read_wallet(json_db, db_env, True, True, "")

    if json_db.get('minversion') > max_version:
        print "Version mismatch (must be <= %d)" % max_version
        exit(1)

    if options.dump:
        print json.dumps(json_db, sort_keys=True, indent=4)

    elif options.key:
        if options.key in private_keys:
            print "Already exists"
        else:    
            db = open_wallet(db_env, writable=True)

            if importprivkey(db, options.key):
                print "Imported successfully"
            else:
                print "Bad private key"

            db.close()

if __name__ == '__main__':
    main()