#!/bin/env python3

import argparse
import json
import os

from pathlib import Path

from configuration import Configuration, RefactoringConfiguration

INLINE_CONSTANT_ID       = 'org.eclipse.jdt.ui.inline.constant'
INLINE_METHOD_ID         = 'org.eclipse.jdt.ui.inline.method'
INLINE_TEMP_ID           = 'org.eclipse.jdt.ui.inline.temp'
EXTRACT_CONSTANT_ID      = 'org.eclipse.jdt.ui.extract.constant'
EXTRACT_METHOD_ID        = 'org.eclipse.jdt.ui.extract.method'
EXTRACT_TEMP_ID          = 'org.eclipse.jdt.ui.extract.temp'
INTRODUCE_INDIRECTION_ID = 'org.eclipse.jdt.ui.introduce.indirection'
RENAME_FIELD_ID          = 'org.eclipse.jdt.ui.rename.field'
RENAME_LOCAL_VARIABLE_ID = 'org.eclipse.jdt.ui.rename.local.variable'
RENAME_METHOD_ID         = 'org.eclipse.jdt.ui.rename.method'
RENAME_TYPE_ID           = 'org.eclipse.jdt.ui.rename.type'
RENAME_TYPE_PARAMETER_ID = 'org.eclipse.jdt.ui.rename.type.parameter'

DEFAULT_REFACTORING_PARAMETERS = {
    INLINE_CONSTANT_ID : {
        "replace" : "false",
        "remove"  : "false"
    },
    INLINE_METHOD_ID : {
        "mode"   : "0",
        "delete" : "false"
    },
    INLINE_TEMP_ID : {
    },
    EXTRACT_CONSTANT_ID : {
        "replace"    : "false",
        "qualify"    : "false",
        "visibility" : "2",
        "name"       : "_x_"
    },
    EXTRACT_METHOD_ID : {
	"visibility" : "2",
        "comments"   : "false",
        "replace"    : "true",
        "exceptions" : "false",
        "name"       : "_x_"
    },
    EXTRACT_TEMP_ID : {
        "name"                 : "_x_",
        "replace"              : "false",
        "replaceAllInThisFile" : "false",
        "final"                : "true",
        "varType"              : "false"
    },
    INTRODUCE_INDIRECTION_ID : {
        "name"       : "_x_",
        "references" : "true"
    },
    RENAME_FIELD_ID : {
        "name"       : "_x_",
        "references" : "true",
        "textual"    : "false",
        "getter"     : "false",
        "setter"     : "false",
        "delegate"   : "false",
        "deprecate"  : "false"
    },
    RENAME_LOCAL_VARIABLE_ID : {
        "name"       : "_x_",
        "references" : "true"
    },
    RENAME_METHOD_ID : {
        "name"      : "_x_",
        "delegate"  : "false",
        "deprecate" : "false"
    },
    RENAME_TYPE_ID : {
        "name"                : "X",
        "patterns"            : "",
        "references"          : "true",
        "textual"             : "false",
        "qualified"           : "false",
        "similarDeclarations" : "false",
        "matchStrategy"       : "1"
    },
    RENAME_TYPE_PARAMETER_ID : {
        "name"       : "_x_",
        "references" : "true"
    }
}

x_names = ["x", "xxxxxxxx", "xxxxxxxxxxxxxxxx"]
X_names = ["X", "Xxxxxxxx", "Xxxxxxxxxxxxxxxx"]
REFACTORING_PARAMETERS = {
    INLINE_CONSTANT_ID : {},
    INLINE_METHOD_ID   : {},
    INLINE_TEMP_ID     : {},
    EXTRACT_CONSTANT_ID : {
        "name"       : x_names,
        "visibility" : ["0", "1", "2", "4"],
        "qualify"    : ["true", "false"]
    },
    EXTRACT_METHOD_ID : {
        "name"       : x_names,
        "visibility" : ["0", "1", "2", "4"]
    },
    EXTRACT_TEMP_ID : {
        "name"  : x_names,
        "final" : ["true", "false"]
    },
    INTRODUCE_INDIRECTION_ID : {
        "name"       : x_names,
        "references" : ["true", "false"]
    },
    RENAME_FIELD_ID : {
        "name" : x_names
    },
    RENAME_LOCAL_VARIABLE_ID : {
        "name" : x_names
    },
    RENAME_METHOD_ID : {
        "name" : x_names
    },
    RENAME_TYPE_ID : {
        "name" : X_names
    },
    RENAME_TYPE_PARAMETER_ID : {
        "name" : X_names
    }
}

def id_list(name, id, config):
    filter = { 'id' : id }
    view   = { name : [ filter ] }
    return (name, filter, config, view)

# Split descriptors of different types into separate lists.
def default_lists_and_views(refactoring_parameters):
    global INLINE_CONSTANT_ID
    global INLINE_METHOD_ID
    global INLINE_TEMP_ID
    global EXTRACT_CONSTANT_ID
    global EXTRACT_METHOD_ID
    global EXTRACT_TEMP_ID
    global INTRODUCE_INDIRECTION_ID
    global RENAME_FIELD_ID
    global RENAME_LOCAL_VARIABLE_ID
    global RENAME_METHOD_ID
    global RENAME_TYPE_ID
    global RENAME_TYPE_PARAMETER_ID

    name_and_ids = [
        ('inline_constant'      , INLINE_CONSTANT_ID),
        ('inline_method'        , INLINE_METHOD_ID),
        ('inline_temp'          , INLINE_TEMP_ID),
        ('extract_constant'     , EXTRACT_CONSTANT_ID),
        ('extract_method'       , EXTRACT_METHOD_ID),
        ('extract_temp'         , EXTRACT_TEMP_ID),
        ('introduce_indirection', INTRODUCE_INDIRECTION_ID),
        ('rename_field'         , RENAME_FIELD_ID),
        ('rename_local_variable', RENAME_LOCAL_VARIABLE_ID),
        ('rename_method'        , RENAME_METHOD_ID),
        ('rename_type'          , RENAME_TYPE_ID),
        ('rename_type_parameter', RENAME_TYPE_PARAMETER_ID)
    ]
    return [
        id_list(*name_and_id, refactoring_parameters[name_and_id[1]])
        for name_and_id in name_and_ids
    ]

def create_workload(args, x, parameters, lists_and_views):
    global DEFAULT_REFACTORING_PARAMETERS

    bm       = parameters['bm']
    workload = parameters['bm_workload']

    x_location = Path(args.x_location) / x
    w_location = x_location / 'workloads' / bm / workload
    w_params   = w_location / 'parameters.txt'
    w_lists    = w_location / 'lists'
    w_views    = w_location / 'views'

    w_location.mkdir(parents = True, exist_ok = True)
    w_lists.mkdir(exist_ok = True)
    w_views.mkdir(exist_ok = True)

    if not (w_lists / 'default.args').exists():
        with open(w_lists / 'default.args', 'w') as f:
            f.write(json.dumps(DEFAULT_REFACTORING_PARAMETERS, sort_keys = True) + os.linesep)

    Configuration().init_from_dict(parameters).store_options(w_params)

    for name, filter, config, view in lists_and_views:

        (w_lists / name).mkdir(parents = True)

        q_filter = w_lists / name / 'q.filter'
        q_config = w_lists / name / 'q.config'
        q_params = w_lists / name / 'q.params'
        q_view   = w_views / (name + '.json')

        with open(q_filter, 'w') as f:
            f.write(json.dumps(filter, sort_keys = True) + os.linesep)

        refactoring_configuration = RefactoringConfiguration().init_from_dict(config)

        refactoring_configuration.store_options(q_config)

        combinations = refactoring_configuration.get_all_combinations()
        if len(combinations) == 0:
            # Add default empty mapping to accept the
            # input opportunity in its original form. 
            combinations.append(RefactoringConfiguration())

        with open(q_params, 'w') as f:
            for combination in combinations:
                f.write(json.dumps(combination._values, sort_keys = True) + os.linesep)

        with open(q_view, 'w') as f:
            f.write(json.dumps(view, sort_keys = True) + os.linesep)

def main(args):
    global REFACTORING_PARAMETERS

    #
    # jacop
    #

    jacop_mzc18_1_parameters = {
        'bm'             : 'jacop',
        'bm_version'     : '1.0',
        'bm_workload'    : 'mzc18_1',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['1G'],
        'stack_size'     : ['32M']
    }
    create_workload(args, 'jacop', jacop_mzc18_1_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    jacop_mzc18_2_parameters = {
        'bm'             : 'jacop',
        'bm_version'     : '1.0',
        'bm_workload'    : 'mzc18_2',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['1G'],
        'stack_size'     : ['32M']
    }
    create_workload(args, 'jacop', jacop_mzc18_2_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    jacop_mzc18_3_parameters = {
        'bm'             : 'jacop',
        'bm_version'     : '1.0',
        'bm_workload'    : 'mzc18_3',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['1G'],
        'stack_size'     : ['32M']
    }
    create_workload(args, 'jacop', jacop_mzc18_3_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    jacop_mzc18_4_parameters = {
        'bm'             : 'jacop',
        'bm_version'     : '1.0',
        'bm_workload'    : 'mzc18_4',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['1G'],
        'stack_size'     : ['32M']
    }
    create_workload(args, 'jacop', jacop_mzc18_4_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    #
    # batik
    #

    batik_small_parameters = {
        'bm'             : 'batik',
        'bm_version'     : '1.0',
        'bm_workload'    : 'small',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'batik', batik_small_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    batik_default_parameters = {
        'bm'             : 'batik',
        'bm_version'     : '1.0',
        'bm_workload'    : 'default',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'batik', batik_default_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    #
    # xalan
    #

    xalan_small_parameters = {
        'bm'             : 'xalan',
        'bm_version'     : '1.0',
        'bm_workload'    : 'small',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'xalan', xalan_small_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    xalan_default_parameters = {
        'bm'             : 'xalan',
        'bm_version'     : '1.0',
        'bm_workload'    : 'default',
        'source_version' : '8',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'xalan', xalan_default_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    #
    # lusearch
    #

    lusearch_small_parameters = {
        'bm'             : 'lusearch',
        'bm_version'     : '1.0',
        'bm_workload'    : 'small',
        'source_version' : '11',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'lusearch', lusearch_small_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    lusearch_default_parameters = {
        'bm'             : 'lusearch',
        'bm_version'     : '1.0',
        'bm_workload'    : 'default',
        'source_version' : '11',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'lusearch', lusearch_default_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    #
    # luindex
    #

    luindex_small_parameters = {
        'bm'             : 'luindex',
        'bm_version'     : '1.0',
        'bm_workload'    : 'small',
        'source_version' : '11',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'luindex', luindex_small_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

    luindex_default_parameters = {
        'bm'             : 'luindex',
        'bm_version'     : '1.0',
        'bm_workload'    : 'default',
        'source_version' : '11',
        'target_version' : ['17'],
        'jdk'            : ['17.0.12-oracle', '17.0.14-tem'],
        'jre'            : ['17.0.12-oracle', '17.0.14-tem'],
        'heap_size'      : ['2G'], # Using explicit default.
        'stack_size'     : ['1M']  # Using explicit default.
    }
    create_workload(args, 'luindex', luindex_default_parameters, default_lists_and_views(REFACTORING_PARAMETERS))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-location', default = 'experiments', required = False,
        help = "Path to  location.")
    args = parser.parse_args()
    main(args)

