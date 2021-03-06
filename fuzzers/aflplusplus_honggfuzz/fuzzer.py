# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Dummy line to force rebuild.
"""Integration code for AFLplusplus fuzzer."""

import os
import shutil

from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def build():
    """Build benchmark."""
    aflplusplus_fuzzer.build('cmplog')
    shutil.copy('/afl/honggfuzz.so', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    os.environ['AFL_CUSTOM_MUTATOR_LIBRARY'] = '/out/honggfuzz.so'
    os.environ['AFL_CUSTOM_MUTATOR_ONLY'] = '1'
    flags = []
    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=flags)
