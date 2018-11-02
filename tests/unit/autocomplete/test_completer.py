# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.testutils import unittest, mock
from awscli.autocomplete import completer, parser

from tests.unit.autocomplete import InMemoryIndex


class TestAutoCompleter(unittest.TestCase):
    def setUp(self):
        self.parser = mock.Mock(spec=parser.CLIParser)
        self.parsed_result = parser.ParsedResult()
        self.parser.parse.return_value = self.parsed_result

    def test_delegates_to_autocompleters(self):
        mock_complete = mock.Mock(spec=completer.BaseCompleter)
        mock_complete.complete.return_value = ['ec2', 'ecs']
        auto_complete = completer.AutoCompleter(
            self.parser, completers=[mock_complete])

        results = auto_complete.autocomplete('aws e')
        self.assertEqual(results, ['ec2', 'ecs'])
        self.parser.parse.assert_called_with('aws e', None)
        mock_complete.complete.assert_called_with(self.parsed_result)

    def test_stops_processing_when_list_returned(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        second.complete.return_value = ['ec2', 'ecs']

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), ['ec2', 'ecs'])

        first.complete.assert_called_with(self.parsed_result)
        second.complete.assert_called_with(self.parsed_result)

    def test_returns_empty_list_if_no_completers_have_results(self):
        first = mock.Mock(spec=completer.BaseCompleter)
        second = mock.Mock(spec=completer.BaseCompleter)

        first.complete.return_value = None
        second.complete.return_value = None

        auto_complete = completer.AutoCompleter(
            self.parser, completers=[first, second])
        self.assertEqual(auto_complete.autocomplete('aws e'), [])

        first.complete.assert_called_with(self.parsed_result)
        second.complete.assert_called_with(self.parsed_result)


class TestModelIndexCompleter(unittest.TestCase):
    def setUp(self):
        self.index = InMemoryIndex({
            'command_names': {
                '': ['aws'],
                'aws': ['ec2', 'ecs', 's3'],
                'aws.ec2': ['describe-instances'],
            },
            'arg_names': {
                '': {
                    'aws': ['region', 'endpoint-url'],
                },
                'aws.ec2': {
                    'describe-instances': ['instance-ids', 'reserve'],
                }
            },
        })
        self.parser = parser.CLIParser(self.index)


        self.completer = completer.ModelIndexCompleter(self.index)

    def test_does_not_complete_if_unparsed_items(self):
        parsed = self.parser.parse('aws foo ')
        self.assertIsNone(self.completer.complete(parsed))

    def test_does_complete_if_last_fragment_is_none(self):
        parsed = self.parser.parse('aws')
        self.assertIsNone(self.completer.complete(parsed))

    def test_can_prefix_match_services(self):
        parsed = parser.ParsedResult(
            current_command='aws', lineage=[],
            last_fragment='e',
        )
        parsed = self.parser.parse('aws e')
        self.assertEqual(self.completer.complete(parsed), ['ec2', 'ecs'])

    def test_returns_all_results_when_last_fragment_empty(self):
        parsed = self.parser.parse('aws ')
        self.assertEqual(self.completer.complete(parsed), ['ec2', 'ecs', 's3'])

    def test_can_autocomplete_global_param(self):
        parsed = self.parser.parse('aws --re')
        self.assertEqual(self.completer.complete(parsed), ['--region'])

    def test_can_combine_global_and_command_params(self):
        parsed = self.parser.parse('aws ec2 describe-instances --r')
        self.assertEqual(self.completer.complete(parsed),
                         ['--reserve', '--region'])

    def test_no_autocompletions_if_nothing_matches(self):
        parsed = self.parser.parse('aws --foo')
        self.assertEqual(self.completer.complete(parsed), [])
