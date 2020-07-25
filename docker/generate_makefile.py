# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Generates Makefile containing docker image targets."""

from experiment.build import docker_images
from common import yaml_utils
import argparse
import os

BASE_TAG = "gcr.io/fuzzbench"
BENCHMARKS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, 'benchmarks')
FUZZERS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, 'fuzzers')


def print_oss_fuzz_benchmark_definition(oss_fuzz_benchmarks):
    for benchmark in oss_fuzz_benchmarks:
        oss_fuzz_yaml = yaml_utils.read(os.path.join(BENCHMARKS_DIR,
                                                    benchmark,
                                                    'oss-fuzz.yaml'))
        print(benchmark + '-project-name=' + oss_fuzz_yaml['project'])
        print(benchmark + '-fuzz-target=' + oss_fuzz_yaml['fuzz_target'])
        if not oss_fuzz_yaml['commit']:
            oss_fuzz_yaml['commit'] = ""
        print(benchmark + '-commit=' + oss_fuzz_yaml['commit'])
        print()


def get_fuzzers_and_benchmarks():
    fuzzers = []
    benchmarks = []
    oss_fuzz_benchmarks = []

    for benchmark in os.listdir(BENCHMARKS_DIR):
        benchmark_path = os.path.join(BENCHMARKS_DIR, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
        if os.path.exists(os.path.join(benchmark_path, 'oss-fuzz.yaml')):
            oss_fuzz_benchmarks.append(benchmark)
        elif os.path.exists(os.path.join(benchmark_path, 'build.sh')):
            benchmarks.append(benchmark)

    for fuzzer in os.listdir(FUZZERS_DIR):
        fuzzer_dir = os.path.join(FUZZERS_DIR, fuzzer)
        if not os.path.isdir(fuzzer_dir):
            continue
        fuzzers.append(fuzzer)

    return fuzzers, benchmarks, oss_fuzz_benchmarks


# TODO(Tanq16): Add unit test for this.
def print_makefile_build_template(name, image):
    """Prints the generated makefile to stdout."""
    print(name + ':', end='')
    if 'depends_on' in image:
        for dep in image['depends_on']:
            print(' ' + dep, end='')
    print()
    print('\tdocker build \\')
    print('\t--tag ' + BASE_TAG + '/' + image['tag'] + ' \\')
    print('\t--cache-from ' + BASE_TAG + '/' + image['tag'] + ' \\')
    print('\t--build-arg BUILDKIT_INLINE_CACHE=1 \\')
    if 'build_arg' in image:
        for arg in image['build_arg']:
            print('\t--build-arg ' + arg + ' \\')
    if 'dockerfile' in image:
        print('\t--file ' + image['dockerfile'] + ' \\')
    print('\t' + image['context'])
    print()


def print_makefile_run_template(name, image, oss_fuzz=False):
    oss_fuzz_string = "oss-fuzz-" if oss_fuzz else ""
    for run_template in ('test', 'debug', 'test-run'):
        print(name.format(run_template=run_template) + ":", end="")
        for dep in image['depends_on']:
            print(' ' + dep.format(oss_fuzz_string=oss_fuzz_string), end='')
        print()
        print('\tdocker run \\')
        if not run_template == 'test-run':
            print('\t--cpus=1 \\')
        print('\t--cap-add SYS_NICE \\')
        print('\t--cap-add SYS_PTRACE \\')
        for var in image['env_vars']:
            if var.startswith('FUZZ_TARGET') and not oss_fuzz:
                continue
            print('\t-e ' + var + ' \\')
        print('\t', end='')
        if run_template == 'test-run':
            print('-e MAX_TOTAL_TIME=20 \\\n\t-e SNAPSHOT_PERIOD=10 \\\n\t', end='')
        else:
            if run_template == 'debug':
                print('--entrypoint "/bin/bash" \\\n\t', end='')
            print('-it ', end='')
        print(BASE_TAG + '/' + image['tag'])
        print()


def print_makefile(name, image, oss_fuzz=False):
    if "{run_template}" in name:
        print_makefile_run_template(name, image, oss_fuzz)
    else:
        print_makefile_build_template(name, image)


def main():
    """Generates Makefile with docker image build rules."""
    fuzzers, benchmarks, oss_fuzz_benchmarks = get_fuzzers_and_benchmarks()

    buildable_images = docker_images.get_images_to_build(fuzzers, benchmarks)
    buildable_images_oss_fuzz = docker_images.get_images_to_build(fuzzers,
                                                                oss_fuzz_benchmarks,
                                                                oss_fuzz=True,
                                                                skip_base_images=True)
    all_benchmarks = benchmarks + oss_fuzz_benchmarks
    
    # print('cache_from = $(if ${RUNNING_ON_CI},--cache-from {fuzzer},)')
    print('export DOCKER_BUILDKIT := 1')

    # Print oss-fuzz benchmarks property variables. 
    print_oss_fuzz_benchmark_definition(oss_fuzz_benchmarks)
    
    for name, image in buildable_images.items():
        print_makefile(name, image)
    for name, image in buildable_images_oss_fuzz.items():
        print_makefile(name, image, oss_fuzz=True)

    # Print build targets for all fuzzer-benchmark pairs.
    for fuzzer in fuzzers:
        image_type = "runner"
        if fuzzer in ('coverage', 'coverage_source_based'):
            image_type = "builder"
        for benchmark in benchmarks:
            print('build-{fuzzer}-{benchmark}: .{fuzzer}-{benchmark}-{image_type}\n'.format(fuzzer=fuzzer, benchmark=benchmark, image_type=image_type))
        for benchmark in oss_fuzz_benchmarks:
            print('build-{fuzzer}-{benchmark}: .{fuzzer}-{benchmark}-oss-fuzz-{image_type}\n'.format(fuzzer=fuzzer, benchmark=benchmark, image_type=image_type))
        print()

    # Print fuzzer-all benchmarks build targets.
    for fuzzer in fuzzers:
        all_build_targets = ' '.join([
            'build-{0}-{1}'.format(fuzzer, benchmark)
            for benchmark in all_benchmarks
        ])
        print('build-{fuzzer}-all: {all_targets}'.format(
            fuzzer=fuzzer, all_targets=all_build_targets))
    
    # Print all targets build target.
    all_build_targets = ' '.join(
        ['build-{0}-all'.format(name) for name in fuzzers])
    print('build-all: {all_targets}'.format(all_targets=all_build_targets))
    

if __name__ == '__main__':
    main()
