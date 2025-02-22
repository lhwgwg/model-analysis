# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for example count metric."""

from absl.testing import parameterized
import apache_beam as beam
from apache_beam.testing import util
import tensorflow as tf
from tensorflow_model_analysis.eval_saved_model import testutil
from tensorflow_model_analysis.metrics import example_count
from tensorflow_model_analysis.metrics import metric_types
from tensorflow_model_analysis.metrics import metric_util


class ExampleCountTest(testutil.TensorflowModelAnalysisTest,
                       parameterized.TestCase):

  @parameterized.named_parameters(
      ('unweighted', '', '', False), ('basic', '', '', True),
      ('multi-model', 'model', '', True), ('multi-output', '', 'output', True),
      ('multi-model-multi-output', 'model', 'output', True))
  def testExampleCount(self, model_name, output_name, example_weighted):
    metric = example_count.ExampleCount().computations(
        model_names=[model_name],
        output_names=[output_name],
        example_weighted=example_weighted)[0]

    example0 = {'labels': None, 'predictions': None, 'example_weights': [0.0]}
    example1 = {'labels': None, 'predictions': None, 'example_weights': [0.5]}
    example2 = {'labels': None, 'predictions': None, 'example_weights': [1.0]}
    example3 = {'labels': None, 'predictions': None, 'example_weights': [0.7]}

    if output_name:
      example0['example_weights'] = {output_name: example0['example_weights']}
      example1['example_weights'] = {output_name: example1['example_weights']}
      example2['example_weights'] = {output_name: example2['example_weights']}
      example3['example_weights'] = {output_name: example3['example_weights']}

    if model_name:
      example0['example_weights'] = {model_name: example0['example_weights']}
      example1['example_weights'] = {model_name: example1['example_weights']}
      example2['example_weights'] = {model_name: example2['example_weights']}
      example3['example_weights'] = {model_name: example3['example_weights']}

    with beam.Pipeline() as pipeline:
      # pylint: disable=no-value-for-parameter
      result = (
          pipeline
          | 'Create' >> beam.Create([example0, example1, example2, example3])
          | 'Process' >> beam.Map(metric_util.to_standard_metric_inputs)
          | 'AddSlice' >> beam.Map(lambda x: ((), x))
          | 'ComputeMetric' >> beam.CombinePerKey(metric.combiner))

      # pylint: enable=no-value-for-parameter

      def check_result(got):
        try:
          self.assertLen(got, 1)
          got_slice_key, got_metrics = got[0]
          self.assertEqual(got_slice_key, ())
          example_count_key = metric_types.MetricKey(
              name='example_count',
              model_name=model_name,
              output_name=output_name,
              example_weighted=example_weighted)
          if example_weighted:
            self.assertDictElementsAlmostEqual(
                got_metrics, {example_count_key: (0.0 + 0.5 + 1.0 + 0.7)})
          else:
            self.assertDictElementsAlmostEqual(
                got_metrics, {example_count_key: (1.0 + 1.0 + 1.0 + 1.0)})

        except AssertionError as err:
          raise util.BeamAssertException(err)

      util.assert_that(result, check_result, label='result')


if __name__ == '__main__':
  tf.test.main()
