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
"""Provides the set of buildable images and their dependencies."""

from common import yaml_utils


def _substitute(template, fuzzer, benchmark):
    """Replaces {fuzzer} or {benchmark} with |fuzzer| or |benchmark| in
    |template| string."""
    return template.format(fuzzer=fuzzer, benchmark=benchmark)


def _instantiate_image_obj(name_template, obj_template, fuzzer, benchmark):
    """Instantiates an image object from a template for a |fuzzer| - |benchmark|
    pair."""
    name = _substitute(name_template, fuzzer, benchmark)
    obj = obj_template.copy()
    for key in obj:
        if key in ('build_arg', 'depends_on'):
            obj[key] = [_substitute(item, fuzzer, benchmark) for item in obj[key]]
        else:
            obj[key] = _substitute(obj[key], fuzzer, benchmark)
    return name, obj


def _get_image_type_templates(oss_fuzz):
    """Loads the image types config that contains "templates" describing how to
    build them and their dependencies."""
    all_templates = yaml_utils.read('docker/image_types.yaml')
    templates = {}
    for name, image in all_templates.items():
        if 'base' in name:
            templates[name] = [image]
        if oss_fuzz and 'oss-fuzz' in name:
            templates[name] = image
        if not oss_fuzz and not 'oss-fuzz' in name:
            templates[name] = image
    return templates


def get_images_to_build(fuzzers, benchmarks, oss_fuzz=False, skip_base=False):
    """Returns the set of buildable images."""
    images = {}
    templates = _get_image_type_templates(oss_fuzz)
    for fuzzer in fuzzers:
        for benchmark in benchmarks:
            for name_templ, obj_templ in templates.items():
                if 'base' in name_templ or 'dispatcher' in name_templ:
                    if not skip_base:
                        images[name_templ] = obj_templ
                    continue
                name, obj = _instantiate_image_obj(name_templ, obj_templ, fuzzer,
                                                  benchmark)
                images[name] = obj
    return images
