from __future__ import absolute_import

from unittest import SkipTest

import numpy as np
from holoviews.core.data import Dataset
from holoviews.core.options import Store
from holoviews.element import Graph, TriMesh, circular_layout
from holoviews.element.comparison import ComparisonTestCase
from holoviews.plotting import comms

try:
    from holoviews.plotting.bokeh.util import bokeh_version
    bokeh_renderer = Store.renderers['bokeh']
    from bokeh.models import (NodesAndLinkedEdges, EdgesAndLinkedNodes, Patches)
    from bokeh.models.mappers import CategoricalColorMapper, LinearColorMapper
except :
    bokeh_renderer = None


class BokehGraphPlotTests(ComparisonTestCase):
    
    def setUp(self):
        if not bokeh_renderer:
            raise SkipTest("Bokeh required to test plot instantiation")
        self.previous_backend = Store.current_backend
        Store.current_backend = 'bokeh'
        self.default_comm = bokeh_renderer.comms['default']

        N = 8
        self.nodes = circular_layout(np.arange(N, dtype=np.int32))
        self.source = np.arange(N, dtype=np.int32)
        self.target = np.zeros(N, dtype=np.int32)
        self.weights = np.random.rand(N)
        self.graph = Graph(((self.source, self.target),))
        self.node_info = Dataset(['Output']+['Input']*(N-1), vdims=['Label'])
        self.node_info2 = Dataset(self.weights, vdims='Weight')
        self.graph2 = Graph(((self.source, self.target), self.node_info))
        self.graph3 = Graph(((self.source, self.target), self.node_info2))
        self.graph4 = Graph(((self.source, self.target, self.weights),), vdims='Weight')

    def tearDown(self):
        Store.current_backend = self.previous_backend
        bokeh_renderer.comms['default'] = self.default_comm
        
    def test_plot_simple_graph(self):
        plot = bokeh_renderer.get_plot(self.graph)
        node_source = plot.handles['scatter_1_source']
        edge_source = plot.handles['multi_line_1_source']
        layout_source = plot.handles['layout_source']
        self.assertEqual(node_source.data['index'], self.source)
        self.assertEqual(edge_source.data['start'], self.source)
        self.assertEqual(edge_source.data['end'], self.target)
        layout = {str(int(z)): (x, y) for x, y, z in self.graph.nodes.array()}
        self.assertEqual(layout_source.graph_layout, layout)

    def test_plot_graph_with_paths(self):
        graph = self.graph.clone((self.graph.data, self.graph.nodes, self.graph.edgepaths))
        plot = bokeh_renderer.get_plot(graph)
        node_source = plot.handles['scatter_1_source']
        edge_source = plot.handles['multi_line_1_source']
        layout_source = plot.handles['layout_source']
        self.assertEqual(node_source.data['index'], self.source)
        self.assertEqual(edge_source.data['start'], self.source)
        self.assertEqual(edge_source.data['end'], self.target)
        edges = graph.edgepaths.split()
        self.assertEqual(edge_source.data['xs'], [path.dimension_values(0) for path in edges])
        self.assertEqual(edge_source.data['ys'], [path.dimension_values(1) for path in edges])
        layout = {str(int(z)): (x, y) for x, y, z in self.graph.nodes.array()}
        self.assertEqual(layout_source.graph_layout, layout)

    def test_graph_inspection_policy_nodes(self):
        plot = bokeh_renderer.get_plot(self.graph)
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIsInstance(renderer.inspection_policy, NodesAndLinkedEdges)
        self.assertEqual(hover.tooltips, [('index', '@{index_hover}')])
        self.assertIn(renderer, hover.renderers)

    def test_graph_inspection_policy_edges(self):
        plot = bokeh_renderer.get_plot(self.graph.opts(plot=dict(inspection_policy='edges')))
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIsInstance(renderer.inspection_policy, EdgesAndLinkedNodes)
        self.assertEqual(hover.tooltips, [('start', '@{start}'), ('end', '@{end}')])
        self.assertIn(renderer, hover.renderers)

    def test_graph_inspection_policy_edges_non_default_names(self):
        graph = self.graph.redim(start='source', end='target')
        plot = bokeh_renderer.get_plot(graph.opts(plot=dict(inspection_policy='edges')))
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIsInstance(renderer.inspection_policy, EdgesAndLinkedNodes)
        self.assertEqual(hover.tooltips, [('source', '@{source}'), ('target', '@{target}')])
        self.assertIn(renderer, hover.renderers)

    def test_graph_inspection_policy_none(self):
        plot = bokeh_renderer.get_plot(self.graph.opts(plot=dict(inspection_policy=None)))
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIs(renderer.inspection_policy, None)

    def test_graph_selection_policy_nodes(self):
        plot = bokeh_renderer.get_plot(self.graph)
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIsInstance(renderer.selection_policy, NodesAndLinkedEdges)
        self.assertIn(renderer, hover.renderers)

    def test_graph_selection_policy_edges(self):
        plot = bokeh_renderer.get_plot(self.graph.opts(plot=dict(selection_policy='edges')))
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIsInstance(renderer.selection_policy, EdgesAndLinkedNodes)
        self.assertIn(renderer, hover.renderers)

    def test_graph_selection_policy_none(self):
        plot = bokeh_renderer.get_plot(self.graph.opts(plot=dict(selection_policy=None)))
        renderer = plot.handles['glyph_renderer']
        hover = plot.handles['hover']
        self.assertIs(renderer.selection_policy, None)

    def test_graph_nodes_categorical_colormapped(self):
        g = self.graph2.opts(plot=dict(color_index='Label'), style=dict(cmap='Set1'))
        plot = bokeh_renderer.get_plot(g)
        cmapper = plot.handles['color_mapper']
        node_source = plot.handles['scatter_1_source']
        glyph = plot.handles['scatter_1_glyph']
        self.assertIsInstance(cmapper, CategoricalColorMapper)
        self.assertEqual(cmapper.factors, ['Output', 'Input'])
        self.assertEqual(node_source.data['Label'], self.node_info['Label'])
        self.assertEqual(glyph.fill_color, {'field': 'Label', 'transform': cmapper})
    
    def test_graph_nodes_numerically_colormapped(self):
        g = self.graph3.opts(plot=dict(color_index='Weight'), style=dict(cmap='viridis'))
        plot = bokeh_renderer.get_plot(g)
        cmapper = plot.handles['color_mapper']
        node_source = plot.handles['scatter_1_source']
        glyph = plot.handles['scatter_1_glyph']
        self.assertIsInstance(cmapper, LinearColorMapper)
        self.assertEqual(cmapper.low, self.weights.min())
        self.assertEqual(cmapper.high, self.weights.max())
        self.assertEqual(node_source.data['Weight'], self.node_info2['Weight'])
        self.assertEqual(glyph.fill_color, {'field': 'Weight', 'transform': cmapper})

    def test_graph_edges_categorical_colormapped(self):
        g = self.graph3.opts(plot=dict(edge_color_index='start'),
                             style=dict(edge_cmap=['#FFFFFF', '#000000']))
        plot = bokeh_renderer.get_plot(g)
        cmapper = plot.handles['edge_colormapper']
        edge_source = plot.handles['multi_line_1_source']
        glyph = plot.handles['multi_line_1_glyph']
        self.assertIsInstance(cmapper, CategoricalColorMapper)
        factors = ['0', '1', '2', '3', '4', '5', '6', '7']
        self.assertEqual(cmapper.factors, factors)
        self.assertEqual(edge_source.data['start_str'], factors)
        self.assertEqual(glyph.line_color, {'field': 'start_str', 'transform': cmapper})

    def test_graph_nodes_numerically_colormapped(self):
        g = self.graph4.opts(plot=dict(edge_color_index='Weight'),
                             style=dict(edge_cmap=['#FFFFFF', '#000000']))
        plot = bokeh_renderer.get_plot(g)
        cmapper = plot.handles['edge_colormapper']
        edge_source = plot.handles['multi_line_1_source']
        glyph = plot.handles['multi_line_1_glyph']
        self.assertIsInstance(cmapper, LinearColorMapper)
        self.assertEqual(cmapper.low, self.weights.min())
        self.assertEqual(cmapper.high, self.weights.max())
        self.assertEqual(edge_source.data['Weight'], self.node_info2['Weight'])
        self.assertEqual(glyph.line_color, {'field': 'Weight', 'transform': cmapper})


class TestBokehTriMeshPlots(ComparisonTestCase):

    def setUp(self):
        if not bokeh_renderer:
            raise SkipTest("Bokeh required to test plot instantiation")
        self.previous_backend = Store.current_backend
        Store.current_backend = 'bokeh'
        self.default_comm = bokeh_renderer.comms['default']

        self.nodes = [(0, 0, 0), (0.5, 1, 1), (1., 0, 2), (1.5, 1, 3)]
        self.simplices = [(0, 1, 2, 0), (1, 2, 3, 1)]
        self.trimesh = TriMesh((self.simplices, self.nodes))
        self.trimesh_weighted = TriMesh((self.simplices, self.nodes), vdims='weight')

    def tearDown(self):
        Store.current_backend = self.previous_backend
        bokeh_renderer.comms['default'] = self.default_comm

    def test_plot_simple_trimesh(self):
        plot = bokeh_renderer.get_plot(self.trimesh)
        node_source = plot.handles['scatter_1_source']
        edge_source = plot.handles['multi_line_1_source']
        layout_source = plot.handles['layout_source']
        self.assertEqual(node_source.data['index'], np.arange(4))
        self.assertEqual(edge_source.data['start'], np.arange(2))
        self.assertEqual(edge_source.data['end'], np.arange(1, 3))
        layout = {str(int(z)): (x, y) for x, y, z in self.trimesh.nodes.array()}
        self.assertEqual(layout_source.graph_layout, layout)

    def test_plot_simple_trimesh_filled(self):
        plot = bokeh_renderer.get_plot(self.trimesh.opts(plot=dict(filled=True)))
        node_source = plot.handles['scatter_1_source']
        edge_source = plot.handles['patches_1_source']
        layout_source = plot.handles['layout_source']
        self.assertIsInstance(plot.handles['patches_1_glyph'], Patches)
        self.assertEqual(node_source.data['index'], np.arange(4))
        self.assertEqual(edge_source.data['start'], np.arange(2))
        self.assertEqual(edge_source.data['end'], np.arange(1, 3))
        layout = {str(int(z)): (x, y) for x, y, z in self.trimesh.nodes.array()}
        self.assertEqual(layout_source.graph_layout, layout)

    def test_graph_edges_categorical_colormapped(self):
        g = self.trimesh.opts(plot=dict(edge_color_index='node1'),
                                       style=dict(edge_cmap=['#FFFFFF', '#000000']))
        plot = bokeh_renderer.get_plot(g)
        cmapper = plot.handles['edge_colormapper']
        edge_source = plot.handles['multi_line_1_source']
        glyph = plot.handles['multi_line_1_glyph']
        self.assertIsInstance(cmapper, CategoricalColorMapper)
        factors = ['0', '1', '2', '3']
        self.assertEqual(cmapper.factors, factors)
        self.assertEqual(edge_source.data['node1_str'], ['0', '1'])
        self.assertEqual(glyph.line_color, {'field': 'node1_str', 'transform': cmapper})

    def test_graph_nodes_numerically_colormapped(self):
        g = self.trimesh_weighted.opts(plot=dict(edge_color_index='weight'),
                                       style=dict(edge_cmap=['#FFFFFF', '#000000']))
        plot = bokeh_renderer.get_plot(g)
        cmapper = plot.handles['edge_colormapper']
        edge_source = plot.handles['multi_line_1_source']
        glyph = plot.handles['multi_line_1_glyph']
        self.assertIsInstance(cmapper, LinearColorMapper)
        self.assertEqual(cmapper.low, 0)
        self.assertEqual(cmapper.high, 1)
        self.assertEqual(edge_source.data['weight'], np.array([0, 1]))
        self.assertEqual(glyph.line_color, {'field': 'weight', 'transform': cmapper})
