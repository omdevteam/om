#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Utilities for 3d data visualization using the Visualization Toolkit (VTK).
"""
import numpy
import vtk

VTK_VERSION = vtk.vtkVersion().GetVTKMajorVersion()


def get_lookup_table(minimum_value, maximum_value, log=False, colorscale="jet", number_of_colors=1000):
    """Create a vtkLookupTable with a specified range, and colorscale.

    Args:
        minimum_value (float): Lowest value the lookup table can display, lower values will be displayed as this value
        maximum_value (float): Highest value the lookup table can display, higher values will be displayed as this value
        log (Optional[bool]): True if the scale is logarithmic
        colorscale (Optional[string]): Accepts the name of any matplotlib colorscale. The lookuptable will
            replicate this scale.
        number_of_colors (Optional[int]): The length of the table. Higher values corresponds to a smoother color scale.

    Returns:
        lookup_table (vtk.vtkLookupTable): A vtk lookup table
    """

    import matplotlib
    import matplotlib.cm
    if log:
        lut = vtk.vtkLogLookupTable()
    else:
        lut = vtk.vtkLookupTable()
    lut.SetTableRange(minimum_value, maximum_value)
    lut.SetNumberOfColors(number_of_colors)
    lut.Build()
    for i in range(number_of_colors):
        color = matplotlib.cm.cmap_d[colorscale](float(i) / float(number_of_colors))
        lut.SetTableValue(i, color[0], color[1], color[2], 1.)
    lut.SetUseBelowRangeColor(True)
    lut.SetUseAboveRangeColor(True)
    return lut


def array_to_float_array(array_in, dtype=None):
    """Convert a numpy array into a vtkFloatArray of vtkDoubleArray, depending on the type of the input.
    This flattens the array and thus the shape is lost.

    Args:
        array_in (numpy.ndarray): The array to convert.
        dtype (Optional[type]): Optionaly convert the array to the specified data. Otherwise the original
            type will be preserved.

    Returns:
        float_array (vtk.vtkFloatArray): A float array of the specified type.
    """
    if dtype is None:
        dtype = array_in.dtype
    if dtype == "float32":
        float_array = vtk.vtkFloatArray()
    elif dtype == "float64":
        float_array = vtk.vtkDoubleArray()
    else:
        raise ValueError("Wrong format of input array, must be float32 or float64")
    if len(array_in.shape) == 2:
        float_array.SetNumberOfComponents(array_in.shape[1])
    elif len(array_in.shape) == 1:
        float_array.SetNumberOfComponents(1)
    else:
        raise ValueError("Wrong shape of array must be 1D or 2D.")
    float_array.SetVoidArray(numpy.ascontiguousarray(array_in, dtype), numpy.product(array_in.shape), 1)
    return float_array


def array_to_vtk(array_in, dtype=None):
    """Convert a numpy array into a vtk array of the specified type. This flattens the array and thus the shape is lost.

    Args:
        array_in (numpy.ndarray): The array to convert.
        dtype (Optional[type]): Optionaly convert the array to the specified data. Otherwise the original type
            will be preserved.

    Returns:
        vtk_array (vtk.vtkFloatArray): A float array of the specified type.
    """
    if dtype is None:
        dtype = numpy.dtype(array_in.dtype)
    else:
        dtype = numpy.dtype(dtype)
    if dtype == numpy.float32:
        vtk_array = vtk.vtkFloatArray()
    elif dtype == numpy.float64:
        vtk_array = vtk.vtkDoubleArray()
    elif dtype == numpy.uint8:
        vtk_array = vtk.vtkUnsignedCharArray()
    elif dtype == numpy.int8:
        vtk_array = vtk.vtkCharArray()
    else:
        raise ValueError("Wrong format of input array, must be float32 or float64")
    if len(array_in.shape) != 1 and len(array_in.shape) != 2:
        raise ValueError("Wrong shape: array must be 1D")
    vtk_array.SetNumberOfComponents(1)
    vtk_array.SetVoidArray(numpy.ascontiguousarray(array_in.flatten(), dtype), numpy.product(array_in.shape), 1)
    return vtk_array


def array_to_image_data(array_in, dtype=None):
    """Convert a numpy array to vtkImageData. Image data is a 3D object, thus the input must be 3D.

    Args:
        array_in (numpy.ndarray): Array to convert to vtkImageData. Must be 3D.
        dtype (Optional[type]): Optionaly convert the array to the specified data. Otherwise the original
            type will be preserved.

    Returns:
        image_data (vtk.vtkImageData): Image data containing the data from the array.
    """
    if len(array_in.shape) != 3:
        raise ValueError("Array must be 3D for conversion to vtkImageData")
    array_flat = array_in.flatten()
    float_array = array_to_float_array(array_flat, dtype)
    image_data = vtk.vtkImageData()
    image_data.SetDimensions(*array_in.shape)
    image_data.GetPointData().SetScalars(float_array)
    return image_data


def window_to_png(render_window, file_name, magnification=1):
    """Take a screen shot of a specific vt render window and save it to file.

    Args:
        render_window (vtk.vtkRenderWindow): The render window window to capture.
        file_name (string): A png file with this name will be created from the provided window.
        magnification (Optional[int]): Increase the resolution of the output file by this factor
    """
    magnification = int(magnification)
    window_to_image_filter = vtk.vtkWindowToImageFilter()
    window_to_image_filter.SetInput(render_window)
    window_to_image_filter.SetMagnification(magnification)
    window_to_image_filter.SetInputBufferTypeToRGBA()
    window_to_image_filter.Update()

    writer = vtk.vtkPNGWriter()
    writer.SetFileName(file_name)
    writer.SetInputConnection(window_to_image_filter.GetOutputPort())
    writer.Write()


def poly_data_to_actor(poly_data, lut):
    """Create a vtkActor from a vtkPolyData. This circumvents the need to create a vtkMapper by internally
    using a very basic vtkMapper

    Args:
        poly_data (vtk.vtkPolyData): vtkPolyData object.
        lut (vtk.vtkLookupTable): The vtkLookupTable specifies the colorscale to use for the maper.

    Returns:
        actor (vtk.vtkActor): Actor to display the provided vtkPolyData
    """
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly_data)
    mapper.SetLookupTable(lut)
    mapper.SetUseLookupTableScalarRange(True)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    return actor


class IsoSurface(object):
    """Create and plot isosurfaces.

    Args:
        volume (numpy.ndimage): 3D floating point array.
        level (float or list of float): The threshold level for the isosurface, or a list of such levels.
    """
    def __init__(self, volume, level=None):
        self._surface_algorithm = None
        self._renderer = None
        self._actor = None
        self._mapper = None
        self._volume_array = None

        self._float_array = vtk.vtkFloatArray()
        self._image_data = vtk.vtkImageData()
        self._image_data.GetPointData().SetScalars(self._float_array)
        self._setup_data(volume)

        self._surface_algorithm = vtk.vtkMarchingCubes()
        self._surface_algorithm.SetInputData(self._image_data)
        self._surface_algorithm.ComputeNormalsOn()

        if level is not None:
            try:
                self.set_multiple_levels(iter(level))
            except TypeError:
                self.set_level(0, level)

        self._mapper = vtk.vtkPolyDataMapper()
        self._mapper.SetInputConnection(self._surface_algorithm.GetOutputPort())
        self._mapper.ScalarVisibilityOn()
        self._actor = vtk.vtkActor()
        self._actor.SetMapper(self._mapper)

    def _setup_data(self, volume):
        """Create the numpy array self._volume_array and vtk array self._float_array and make them share data.

        Args:
            volume (numpy.ndimage): This data will populate both the created numpy and vtk objects.
        """
        self._volume_array = numpy.zeros(volume.shape, dtype="float32", order="C")
        self._volume_array[:] = volume
        self._float_array.SetNumberOfValues(numpy.product(volume.shape))
        self._float_array.SetNumberOfComponents(1)
        self._float_array.SetVoidArray(self._volume_array, numpy.product(volume.shape), 1)
        self._image_data.SetDimensions(*self._volume_array.shape)

    def set_renderer(self, renderer):
        """Set the renderer of the isosurface and remove any existing renderer.

        Args:
            renderer (vtk.vtkRenderer): Give this renderer controll over all the surface actors.
        """
        if self._actor is None:
            raise RuntimeError("Actor does not exist.")
        if self._renderer is not None:
            self._renderer.RemoveActor(self._actor)
        self._renderer = renderer
        self._renderer.AddActor(self._actor)

    def set_multiple_levels(self, levels):
        """Remova any current surface levels and add the ones from the provided list.

        Args:
            levels (list of float): Levels for the isosurface, in absolute values (not e.g. ratios)
        """
        self._surface_algorithm.SetNumberOfContours(0)
        for index, this_level in enumerate(levels):
            self._surface_algorithm.SetValue(index, this_level)
        self._render()

    def get_levels(self):
        """Return a list of the current surface levels.

        Returns:
            levels (list of floats): The current surface levels.
        """
        return [self._surface_algorithm.GetValue(index)
                for index in range(self._surface_algorithm.GetNumberOfContours())]

    def add_level(self, level):
        """Add a single surface level.

        Args:
            level (float): The level of the new surface.
        """
        self._surface_algorithm.SetValue(self._surface_algorithm.GetNumberOfContours(), level)
        self._render()

    def remove_level(self, index):
        """Remove a singel surface level at the provided index.

        Args:
            index (int): The index of the level. If levels were added one by one this corresponds
                to the order in which they were added.
        """
        for index in range(index, self._surface_algorithm.GetNumberOfContours()-1):
            self._surface_algorithm.SetValue(index, self._surface_algorithm.GetValue(index+1))
        self._surface_algorithm.SetNumberOfContours(self._surface_algorithm.GetNumberOfContours()-1)
        self._render()

    def set_level(self, index, level):
        """Change the value of an existing surface level.

        Args:
            index (int): The index of the level to change. If levels were added one by one this corresponds to
                the order in which they were added.
            level (float): The new level of the surface.
        """
        self._surface_algorithm.SetValue(index, level)
        self._render()

    def set_cmap(self, cmap):
        """Set the colormap. The color is a function of surface level and mainly of relevance when plotting multiple surfaces.

        Args:
            cmap (string): Name of the colormap to use. Supports all colormaps provided by matplotlib.
        """
        self._mapper.ScalarVisibilityOn()
        self._mapper.SetLookupTable(get_lookup_table(self._volume_array.min(), self._volume_array.max(),
                                                     colorscale=cmap))
        self._render()

    def set_color(self, color):
        """Plot all surfaces in this provided color.

        Args:
            color (length 3 iterable): The RGB value of the color.
        """
        self._mapper.ScalarVisibilityOff()
        self._actor.GetProperty().SetColor(color[0], color[1], color[2])
        self._render()

    def set_opacity(self, opacity):
        """Set the opacity of all surfaces. (seting it individually for each surface is not supported)

        Args:
            opacity (float): Value between 0. and 1. where 0. is completely transparent and 1. is completely opaque.
        """
        self._actor.GetProperty().SetOpacity(opacity)
        self._render()

    def _render(self):
        """Render if a renderer is set, otherwise do nothing."""
        if self._renderer is not None:
            self._renderer.GetRenderWindow().Render()

    def set_data(self, volume):
        """Change the data displayed.

        Args:
            volume (numpy.ndarray): The new array. Must have the same shape as the old array."""
        if volume.shape != self._volume_array.shape:
            raise ValueError("New volume must be the same shape as the old one")
        self._volume_array[:] = volume
        self._float_array.Modified()
        self._render()


def plot_isosurface(volume, level=None, opacity=1.):
    """Plot isosurfaces of the provided module.

    Args:
        volume (numpy.ndarray): The 3D numpy array that will be plotted.
        level (float or list of floats): Levels can be iterable or singel value.
        opacity (float): Float between 0. and 1. where 0. is completely transparent and 1. is completely opaque.
    """

    surface_object = IsoSurface(volume, level)
    surface_object.set_opacity(opacity)

    renderer = vtk.vtkRenderer()
    if opacity != 1.:
        renderer.SetUseDepthPeeling(True)
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    interactor.SetInteractorStyle(vtk.vtkInteractorStyleRubberBandPick())

    surface_object.set_renderer(renderer)

    renderer.SetBackground(0., 0., 0.)
    render_window.SetSize(800, 800)
    interactor.Initialize()
    render_window.Render()
    interactor.Start()


def plot_planes(array_in, log=False, cmap=None):
    """Plot the volume at two interactive planes that cut the volume.

    Args:
        array_in (numpy.ndarray): Input array must be 3D.
        log (bool): If true the data will be plotted in logarithmic scale.
        cmap (string): Name of the colormap to use. Supports all colormaps provided by matplotlib.
    """
    array_in = numpy.float64(array_in)
    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    interactor.SetInteractorStyle(vtk.vtkInteractorStyleRubberBandPick())

    if cmap is None:
        import matplotlib as _matplotlib
        cmap = _matplotlib.rcParams["image.cmap"]
    lut = get_lookup_table(max(0., array_in.min()), array_in.max(), log=log, colorscale=cmap)
    picker = vtk.vtkCellPicker()
    picker.SetTolerance(0.005)

    image_data = array_to_image_data(array_in)

    def setup_plane():
        """Create and setup a singel plane."""
        plane = vtk.vtkImagePlaneWidget()
        if VTK_VERSION >= 6:
            plane.SetInputData(image_data)
        else:
            plane.SetInput(image_data)
        plane.UserControlledLookupTableOn()
        plane.SetLookupTable(lut)
        plane.DisplayTextOn()
        plane.SetPicker(picker)
        plane.SetLeftButtonAction(1)
        plane.SetMiddleButtonAction(2)
        plane.SetRightButtonAction(0)
        plane.SetInteractor(interactor)
        return plane

    plane_1 = setup_plane()
    plane_1.SetPlaneOrientationToXAxes()
    plane_1.SetSliceIndex(array_in.shape[0]//2)
    plane_1.SetEnabled(1)
    plane_2 = setup_plane()
    plane_2.SetPlaneOrientationToYAxes()
    plane_2.SetSliceIndex(array_in.shape[1]//2)
    plane_2.SetEnabled(1)

    renderer.SetBackground(0., 0., 0.)
    render_window.SetSize(800, 800)
    interactor.Initialize()
    render_window.Render()
    interactor.Start()


def setup_window(size=(400, 400), background=(1., 1., 1.)):
    """Create a renderer, render_window and interactor and setup connections between them.

    Args:
        size (Optional[length 2 iterable of int]): The size of the window in pixels.
        background (Optional[length 3 iterable of float]): RGB value of the background color.

    Returns:
        renderer (vtk.vtkRenderer): A standard renderer connected to the window.
        render_window (vtk.vtkRenderWindow): With dimensions given in the arguments, or oterwise 400x400 pixels.
        interactor (vtk.vtkRenderWindowInteractor): The interactor will be given the rubber band pick interactor style.
    """
    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetInteractorStyle(vtk.vtkInteractorStyleRubberBandPick())
    interactor.SetRenderWindow(render_window)

    renderer.SetBackground(background[0], background[1], background[2])
    render_window.SetSize(size[0], size[1])

    interactor.Initialize()
    render_window.Render()
    return renderer, render_window, interactor


def scatterplot_3d(data, color=None, point_size=None, cmap="jet", point_shape=None):
    """3D scatter plot.

    Args:
        data (numpy.ndimage): The array must have shape Nx3 where N is the number of points.

        color (Optional[numpy.ndimage]): 1D Array of floating points with same length as the data array.
            These numbers give the color of each point.
            
        point_size (Optional[float]): The size of each points. Behaves differently depending on the point_shape.
            If shape is spheres the size is relative to the scene and if squares the size is relative to the window.
            
        cmap (Optional[str]): Color map
        
        point_shape (Optional["spheres" or "squares"]): "spheres" plots each point as a sphere, recommended for
            small data sets. "squares" plot each point as a square without any 3D structure, recommended for
            large data sets.
    """
    if len(data.shape) != 2 or data.shape[1] != 3:
        raise ValueError("data must have shape (n, 3) where n is the number of points.")
    if point_shape is None:
        if len(data) <= 1000:
            point_shape = "spheres"
        else:
            point_shape = "squares"
    data = numpy.float32(data)
    data_vtk = array_to_float_array(data)
    point_data = vtk.vtkPoints()
    point_data.SetData(data_vtk)
    points_poly_data = vtk.vtkPolyData()
    points_poly_data.SetPoints(point_data)

    if color is not None:
        lut = get_lookup_table(color.min(), color.max())
        color_scalars = array_to_vtk(numpy.float32(color.copy()))
        color_scalars.SetLookupTable(lut)
        points_poly_data.GetPointData().SetScalars(color_scalars)

    if point_shape == "spheres":
        if point_size is None:
            point_size = numpy.array(data).std() / len(data)**(1./3.) / 3.
        glyph_filter = vtk.vtkGlyph3D()
        glyph_filter.SetInputData(points_poly_data)
        sphere_source = vtk.vtkSphereSource()
        sphere_source.SetRadius(point_size)
        glyph_filter.SetSourceConnection(sphere_source.GetOutputPort())
        glyph_filter.SetScaleModeToDataScalingOff()
        if color is not None:
            glyph_filter.SetColorModeToColorByScalar()
        else:
            glyph_filter.SetColorMode(0)
        glyph_filter.Update()
    elif point_shape == "squares":
        if point_size is None:
            point_size = 3
        glyph_filter = vtk.vtkVertexGlyphFilter()
        glyph_filter.SetInputData(points_poly_data)
        glyph_filter.Update()
    else:
        raise ValueError("{0} is not a valid entry for points".format(point_shape))

    poly_data = vtk.vtkPolyData()
    poly_data.ShallowCopy(glyph_filter.GetOutput())

    renderer, render_window, interactor = setup_window()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly_data)
    if color is not None:
        mapper.SetLookupTable(lut)
        mapper.SetUseLookupTableScalarRange(True)

    points_actor = vtk.vtkActor()
    points_actor.SetMapper(mapper)
    points_actor.GetProperty().SetPointSize(point_size)
    points_actor.GetProperty().SetColor(0., 0., 0.)

    axes_actor = vtk.vtkCubeAxesActor()
    axes_actor.SetBounds(points_actor.GetBounds())
    axes_actor.SetCamera(renderer.GetActiveCamera())
    axes_actor.SetFlyModeToStaticTriad()
    axes_actor.GetXAxesLinesProperty().SetColor(0., 0., 0.)
    axes_actor.GetYAxesLinesProperty().SetColor(0., 0., 0.)
    axes_actor.GetZAxesLinesProperty().SetColor(0., 0., 0.)
    for i in range(3):
        axes_actor.GetLabelTextProperty(i).SetColor(0., 0., 0.)
        axes_actor.GetTitleTextProperty(i).SetColor(0., 0., 0.)

    renderer.AddActor(points_actor)
    renderer.AddActor(axes_actor)

    render_window.Render()
    interactor.Start()
