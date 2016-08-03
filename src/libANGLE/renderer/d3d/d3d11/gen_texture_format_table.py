#!/usr/bin/python
# Copyright 2015 The ANGLE Project Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# gen_texture_format_table.py:
#  Code generation for texture format map
#

from datetime import date
import json
import math
import pprint
import re
import sys

template_texture_format_table_autogen_h = """// GENERATED FILE - DO NOT EDIT.
// Generated by gen_texture_format_table.py using data from texture_format_data.json
//
// Copyright 2016 The ANGLE Project Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//

namespace rx
{{

namespace d3d11
{{

enum ANGLEFormat
{{
{angle_format_enum}
}};

}}  // namespace d3d11

}}  // namespace rx
"""

template_texture_format_table_autogen_cpp = """// GENERATED FILE - DO NOT EDIT.
// Generated by gen_texture_format_table.py using data from texture_format_data.json
//
// Copyright {copyright_year} The ANGLE Project Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// texture_format_table:
//   Queries for full textureFormat information based in internalFormat
//

#include "libANGLE/renderer/d3d/d3d11/texture_format_table.h"

#include "image_util/copyimage.h"
#include "image_util/generatemip.h"
#include "image_util/loadimage.h"

#include "libANGLE/renderer/d3d/d3d11/formatutils11.h"
#include "libANGLE/renderer/d3d/d3d11/renderer11_utils.h"
#include "libANGLE/renderer/d3d/d3d11/texture_format_table_utils.h"

using namespace angle;

namespace rx
{{

namespace d3d11
{{

const ANGLEFormatSet &GetANGLEFormatSet(ANGLEFormat angleFormat,
                                        const Renderer11DeviceCaps &deviceCaps)
{{
    // clang-format off
    switch (angleFormat)
    {{
{angle_format_info_cases}
        default:
            break;
    }}
    // clang-format on

    UNREACHABLE();
    static const ANGLEFormatSet defaultInfo;
    return defaultInfo;
}}

const TextureFormat &GetTextureFormatInfo(GLenum internalFormat,
                                          const Renderer11DeviceCaps &deviceCaps)
{{
    // clang-format off
    switch (internalFormat)
    {{
{texture_format_info_cases}
        default:
            UNREACHABLE();
            break;
    }}
    // clang-format on

    static const TextureFormat defaultInfo(GL_NONE, ANGLE_FORMAT_NONE, nullptr, deviceCaps);
    return defaultInfo;
}}  // GetTextureFormatInfo

}}  // namespace d3d11

}}  // namespace rx
"""

# TODO(oetuaho): Expand this code so that it could generate the gl format info tables as well.
def gl_format_channels(internal_format):
    if internal_format == 'GL_BGR5_A1_ANGLEX':
        return 'bgra'
    if internal_format == 'GL_R11F_G11F_B10F':
        return 'rgb'
    if internal_format == 'GL_RGB5_A1':
        return 'rgba'
    if internal_format.find('GL_RGB10_A2') == 0:
        return 'rgba'

    channels_pattern = re.compile('GL_(COMPRESSED_)?(SIGNED_)?(ETC\d_)?([A-Z]+)')
    match = re.search(channels_pattern, internal_format)
    channels_string = match.group(4)

    if channels_string == 'ALPHA':
        return 'a'
    if channels_string == 'LUMINANCE':
        if (internal_format.find('ALPHA') >= 0):
            return 'la'
        return 'l'
    if channels_string == 'SRGB':
        if (internal_format.find('ALPHA') >= 0):
            return 'rgba'
        return 'rgb'
    if channels_string == 'DEPTH':
        if (internal_format.find('STENCIL') >= 0):
            return 'ds'
        return 'd'
    if channels_string == 'STENCIL':
        return 's'
    return channels_string.lower()

def get_internal_format_initializer(internal_format, angle_format):
    internal_format_initializer = 'nullptr'
    gl_channels = gl_format_channels(internal_format)
    gl_format_no_alpha = gl_channels == 'rgb' or gl_channels == 'l'
    if gl_format_no_alpha and angle_format['channels'] == 'rgba':
        if angle_format['texFormat'] == 'DXGI_FORMAT_BC1_UNORM':
            # BC1 is a special case since the texture data determines whether each block has an alpha channel or not.
            # This if statement is hit by COMPRESSED_RGB_S3TC_DXT1, which is a bit of a mess.
            # TODO(oetuaho): Look into whether COMPRESSED_RGB_S3TC_DXT1 works right in general.
            # Reference: https://www.opengl.org/registry/specs/EXT/texture_compression_s3tc.txt
            pass
        elif 'componentType' not in angle_format:
            raise ValueError('warning: internal format initializer could not be generated and may be needed for ' + internal_format)
        elif angle_format['componentType'] == 'uint' and angle_format['bits']['red'] == 8:
            internal_format_initializer = 'Initialize4ComponentData<GLubyte, 0x00, 0x00, 0x00, 0x01>'
        elif angle_format['componentType'] == 'unorm' and angle_format['bits']['red'] == 8:
            internal_format_initializer = 'Initialize4ComponentData<GLubyte, 0x00, 0x00, 0x00, 0xFF>'
        elif angle_format['componentType'] == 'unorm' and angle_format['bits']['red'] == 16:
            internal_format_initializer = 'Initialize4ComponentData<GLubyte, 0x0000, 0x0000, 0x0000, 0xFFFF>'
        elif angle_format['componentType'] == 'int' and angle_format['bits']['red'] == 8:
            internal_format_initializer = 'Initialize4ComponentData<GLbyte, 0x00, 0x00, 0x00, 0x01>'
        elif angle_format['componentType'] == 'snorm' and angle_format['bits']['red'] == 8:
            internal_format_initializer = 'Initialize4ComponentData<GLbyte, 0x00, 0x00, 0x00, 0x7F>'
        elif angle_format['componentType'] == 'snorm' and angle_format['bits']['red'] == 16:
            internal_format_initializer = 'Initialize4ComponentData<GLushort, 0x0000, 0x0000, 0x0000, 0x7FFF>'
        elif angle_format['componentType'] == 'float' and angle_format['bits']['red'] == 16:
            internal_format_initializer = 'Initialize4ComponentData<GLhalf, 0x0000, 0x0000, 0x0000, gl::Float16One>'
        elif angle_format['componentType'] == 'uint' and angle_format['bits']['red'] == 16:
            internal_format_initializer = 'Initialize4ComponentData<GLushort, 0x0000, 0x0000, 0x0000, 0x0001>'
        elif angle_format['componentType'] == 'int' and angle_format['bits']['red'] == 16:
            internal_format_initializer = 'Initialize4ComponentData<GLshort, 0x0000, 0x0000, 0x0000, 0x0001>'
        elif angle_format['componentType'] == 'float' and angle_format['bits']['red'] == 32:
            internal_format_initializer = 'Initialize4ComponentData<GLfloat, 0x00000000, 0x00000000, 0x00000000, gl::Float32One>'
        elif angle_format['componentType'] == 'int' and angle_format['bits']['red'] == 32:
            internal_format_initializer = 'Initialize4ComponentData<GLint, 0x00000000, 0x00000000, 0x00000000, 0x00000001>'
        elif angle_format['componentType'] == 'uint' and angle_format['bits']['red'] == 32:
            internal_format_initializer = 'Initialize4ComponentData<GLuint, 0x00000000, 0x00000000, 0x00000000, 0x00000001>'
        else:
            raise ValueError('warning: internal format initializer could not be generated and may be needed for ' + internal_format)

    return internal_format_initializer

def get_swizzle_format_id(angle_format_id, angle_format):
    if angle_format_id == 'ANGLE_FORMAT_NONE':
        return 'ANGLE_FORMAT_NONE'
    elif 'swizzleFormat' in angle_format:
        # For some special formats like compressed formats that don't have a clearly defined number
        # of bits per channel, swizzle format needs to be specified manually.
        return angle_format['swizzleFormat']

    if 'bits' not in angle_format:
        raise ValueError('no bits information for determining swizzleformat for format: ' + angle_format_id)

    bits = angle_format['bits']
    max_component_bits = max(bits.itervalues())
    channels_different = not all([component_bits == bits.itervalues().next() for component_bits in bits.itervalues()])

    # The format itself can be used for swizzles if it can be accessed as a render target and
    # sampled and the bit count for all 4 channels is the same.
    if "rtvFormat" in angle_format and "srvFormat" in angle_format and not channels_different and len(angle_format['channels']) == 4:
        return angle_format_id

    b = int(math.ceil(float(max_component_bits) / 8) * 8)

    # Depth formats need special handling, since combined depth/stencil formats don't have a clearly
    # defined component type.
    if angle_format['channels'].find('d') >= 0:
        if b == 24 or b == 32:
            return 'ANGLE_FORMAT_R32G32B32A32_FLOAT'
        if b == 16:
            return 'ANGLE_FORMAT_R16G16B16A16_UNORM'

    if b == 24:
        raise ValueError('unexpected 24-bit format when determining swizzleformat for format: ' + angle_format_id)

    if 'componentType' not in angle_format:
        raise ValueError('no component type information for determining swizzleformat for format: ' + angle_format_id)

    component_type = angle_format['componentType']
    if component_type == 'uint':
        return 'ANGLE_FORMAT_R{}G{}B{}A{}_UINT'.format(b, b, b, b)
    elif component_type == 'int':
        return 'ANGLE_FORMAT_R{}G{}B{}A{}_SINT'.format(b, b, b, b)
    elif component_type == 'unorm':
        return 'ANGLE_FORMAT_R{}G{}B{}A{}_UNORM'.format(b, b, b, b)
    elif component_type == 'snorm':
        return 'ANGLE_FORMAT_R{}G{}B{}A{}_SNORM'.format(b, b, b, b)
    elif component_type == 'float':
        return 'ANGLE_FORMAT_R{}G{}B{}A{}_FLOAT'.format(b, b, b, b)
    else:
        raise ValueError('could not determine swizzleformat based on componentType for format: ' + angle_format_id)

def get_texture_format_item(idx, internal_format, requirements_fn, angle_format_id, angle_format):
    table_data = '';

    internal_format_initializer = get_internal_format_initializer(internal_format, angle_format)

    indent = '            '
    if requirements_fn != None:
        if idx == 0:
            table_data += '            if (' + requirements_fn + '(deviceCaps))\n'
        else:
            table_data += '            else if (' + requirements_fn + '(deviceCaps))\n'
        table_data += '            {\n'
        indent += '    '

    table_data += indent + 'static const TextureFormat textureFormat(internalFormat,\n'
    table_data += indent + '                                         ' + angle_format_id + ',\n'
    table_data += indent + '                                         ' + internal_format_initializer + ',\n'
    table_data += indent + '                                         deviceCaps);\n'
    table_data += indent + 'return textureFormat;\n'

    if requirements_fn != None:
        table_data += '            }\n'

    return table_data

def parse_json_into_switch_texture_format_string(json_map, json_data):
    table_data = ''
    angle_format_map = {}

    for internal_format_item in sorted(json_map.iteritems()):
        internal_format = internal_format_item[0]
        table_data += '        case ' + internal_format + ':\n'
        table_data += '        {\n'

        if isinstance(json_map[internal_format], basestring):
            angle_format_id = json_map[internal_format]
            table_data += get_texture_format_item(0, internal_format, None, angle_format_id, json_data[angle_format_id])
        else:
            for idx, requirements_map in enumerate(sorted(json_map[internal_format].iteritems())):
                angle_format_id = requirements_map[1]
                table_data += get_texture_format_item(idx, internal_format, requirements_map[0], angle_format_id, json_data[angle_format_id])
            table_data += '            else\n'
            table_data += '            {\n'
            table_data += '                break;\n'
            table_data += '            }\n'

        table_data += '        }\n'

    return table_data

def get_channel_struct(angle_format):
    if 'bits' not in angle_format:
        return None
    bits = angle_format['bits']
    if 'depth' in bits or 'stencil' in bits:
        return None

    if 'channelStruct' in angle_format:
        return angle_format['channelStruct']

    struct_name = ''
    for channel in angle_format['channels']:
        if channel == 'r':
            struct_name += 'R{}'.format(bits['red'])
        if channel == 'g':
            struct_name += 'G{}'.format(bits['green'])
        if channel == 'b':
            struct_name += 'B{}'.format(bits['blue'])
        if channel == 'a':
            struct_name += 'A{}'.format(bits['alpha'])
    if angle_format['componentType'] == 'float':
        struct_name += 'F'
    if angle_format['componentType'] == 'int' or angle_format['componentType'] == 'snorm':
        struct_name += 'S'
    return struct_name

def get_mip_generation_function(angle_format):
    channel_struct = get_channel_struct(angle_format)
    if channel_struct == None:
        return 'nullptr'
    return 'GenerateMip<' + channel_struct + '>'

def get_color_read_function(angle_format):
    channel_struct = get_channel_struct(angle_format)
    if channel_struct == None:
        return 'nullptr'
    component_type_map = {
        'uint': 'GLuint',
        'int': 'GLint',
        'unorm': 'GLfloat',
        'snorm': 'GLfloat',
        'float': 'GLfloat'
    }
    return 'ReadColor<' + channel_struct + ', '+ component_type_map[angle_format['componentType']] + '>'

def get_blit_srv_format(angle_format):
    if 'channels' not in angle_format:
        return 'DXGI_FORMAT_UNKNOWN'
    if 'r' in angle_format['channels'] and angle_format['componentType'] in ['int', 'uint']:
        return angle_format['rtvFormat']

    return angle_format["srvFormat"] if "srvFormat" in angle_format else "DXGI_FORMAT_UNKNOWN"


format_entry_template = """{space}{{
{space}    static const ANGLEFormatSet formatInfo({formatName},
{space}                                           {glInternalFormat},
{space}                                           {fboImplementationInternalFormat},
{space}                                           {texFormat},
{space}                                           {srvFormat},
{space}                                           {rtvFormat},
{space}                                           {dsvFormat},
{space}                                           {blitSRVFormat},
{space}                                           {swizzleFormat},
{space}                                           {mipGenerationFunction},
{space}                                           {colorReadFunction});
{space}    return formatInfo;
{space}}}
"""

split_format_entry_template = """{space}    {condition}
{space}    {{
{space}        static const ANGLEFormatSet formatInfo({formatName},
{space}                                               {glInternalFormat},
{space}                                               {fboImplementationInternalFormat},
{space}                                               {texFormat},
{space}                                               {srvFormat},
{space}                                               {rtvFormat},
{space}                                               {dsvFormat},
{space}                                               {blitSRVFormat},
{space}                                               {swizzleFormat},
{space}                                               {mipGenerationFunction},
{space}                                               {colorReadFunction});
{space}        return formatInfo;
{space}    }}
"""

def json_to_table_data(format_name, prefix, json):

    table_data = ""

    parsed = {
        "space": "        ",
        "formatName": format_name,
        "texFormat": "DXGI_FORMAT_UNKNOWN",
        "srvFormat": "DXGI_FORMAT_UNKNOWN",
        "rtvFormat": "DXGI_FORMAT_UNKNOWN",
        "dsvFormat": "DXGI_FORMAT_UNKNOWN",
        "glInternalFormat": "GL_NONE",
        "condition": prefix,
    }

    for k, v in json.iteritems():
        parsed[k] = v

    if (format_name != "ANGLE_FORMAT_NONE") and (parsed["glInternalFormat"] == "GL_NONE"):
        print("Missing 'glInternalFormat' from " + format_name)
        sys.exit(1)

    if "fboImplementationInternalFormat" not in parsed:
        parsed["fboImplementationInternalFormat"] = parsed["glInternalFormat"]

    # Derived values.
    parsed["blitSRVFormat"] = get_blit_srv_format(parsed)
    parsed["swizzleFormat"] = get_swizzle_format_id(format_name, parsed)
    parsed["mipGenerationFunction"] = get_mip_generation_function(parsed)
    parsed["colorReadFunction"] = get_color_read_function(parsed)

    if len(prefix) > 0:
        return split_format_entry_template.format(**parsed)
    else:
        return format_entry_template.format(**parsed)

def parse_json_into_switch_angle_format_string(json_data):
    table_data = ''
    for angle_format_item in sorted(json_data.iteritems()):
        table_data += '        case ' + angle_format_item[0] + ':\n'
        format_name = angle_format_item[0]
        angle_format = angle_format_item[1]

        fl10plus = {}
        fl9_3 = {}
        split = False

        for k, v in angle_format.iteritems():
            if k == "FL10Plus":
                split = True
                for k2, v2 in v.iteritems():
                    fl10plus[k2] = v2
            elif k == "FL9_3":
                split = True
                for k2, v2 in v.iteritems():
                    fl9_3[k2] = v2
            else:
                fl10plus[k] = v
                fl9_3[k] = v

        if split:
            table_data += "        {\n"
            table_data += json_to_table_data(format_name, "if (OnlyFL10Plus(deviceCaps))", fl10plus)
            table_data += json_to_table_data(format_name, "else", fl9_3)
            table_data += "        }\n"
            table_data += "        break;\n"
        else:
            table_data += json_to_table_data(format_name, "", fl10plus)

    return table_data

def parse_json_into_angle_format_enum_string(json_data):
    enum_data = ''
    index = 0
    for angle_format_item in sorted(json_data.iteritems()):
        if index > 0:
            enum_data += ',\n'
        enum_data += '    ' + angle_format_item[0]
        index += 1
    return enum_data

def reject_duplicate_keys(pairs):
    found_keys = {}
    for key, value in pairs:
        if key in found_keys:
           raise ValueError("duplicate key: %r" % (key,))
        else:
           found_keys[key] = value
    return found_keys

with open('texture_format_map.json') as texture_format_map_file:
    with open('texture_format_data.json') as texture_format_json_file:
        texture_format_map = texture_format_map_file.read()
        texture_format_data = texture_format_json_file.read()
        texture_format_map_file.close()
        texture_format_json_file.close()
        json_map = json.loads(texture_format_map, object_pairs_hook=reject_duplicate_keys)
        json_data = json.loads(texture_format_data, object_pairs_hook=reject_duplicate_keys)

        texture_format_cases = parse_json_into_switch_texture_format_string(json_map, json_data)
        angle_format_cases = parse_json_into_switch_angle_format_string(json_data)
        output_cpp = template_texture_format_table_autogen_cpp.format(
            copyright_year=date.today().year,
            texture_format_info_cases=texture_format_cases,
            angle_format_info_cases=angle_format_cases)
        with open('texture_format_table_autogen.cpp', 'wt') as out_file:
            out_file.write(output_cpp)
            out_file.close()

        enum_data = parse_json_into_angle_format_enum_string(json_data)
        output_h = template_texture_format_table_autogen_h.format(angle_format_enum=enum_data)
        with open('texture_format_table_autogen.h', 'wt') as out_file:
            out_file.write(output_h)
            out_file.close()
