# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
This module contains the definitions of several typed dictionaries that store data
produced or required by OM's functions and classes.
"""

from typing import Any, Dict, Generator, List, Protocol, Tuple, TypedDict, Union

import numpy
from numpy.typing import NDArray

from om.lib.parameters import MonitorParameters


class TypePeakList(TypedDict, total=True):
    """
    Detected peaks information.

    This typed dictionary stores information about a set of peaks found by a
    peak-finding algorithm in a detector data frame.

    Attributes:

        num_peaks: The number of peaks detected in the data frame.

        fs: A list of fractional fs indexes that locate the detected peaks in the data
            frame.

        ss: A list of fractional ss indexes that locate the detected peaks in the data
            frame.

        intensity: A list of integrated intensities for the detected peaks.

        num_pixels: A list storing the number of pixels in each detected peak.

        max_pixel_intensity: A list storing, for each peak, the value of the pixel with
            the maximum intensity.

        snr: A list storing  the signal-to-noise ratio of each detected peak.
    """

    num_peaks: int
    fs: List[float]
    ss: List[float]
    intensity: List[float]
    num_pixels: List[float]
    max_pixel_intensity: List[float]
    snr: List[float]


class TypeJungfrau1MFrameInfo(TypedDict):
    # This typed dictionary is used internally to store additional information
    # required to retrieve Jungfrau 1M frame data.
    h5file: Any
    index: int
    file_timestamp: float


class TypeBeam(TypedDict, total=True):
    """
    A dictionary storing information about the x-ray beam.

    Attributes:

        photon_energy: The photon energy of the beam in eV.

        photon_energy_from: The internal path for the photon energy information in an
            HDF5 data file, in case the beam energy information is extracted from it.

        photon_energy_scale: The scaling factor to be applied to the photon energy, in
            case the provided energy value is not in eV.
    """

    photon_energy: float
    photon_energy_from: str
    photon_energy_scale: float


class TypePanel(TypedDict, total=True):
    """
    A dictionary storing information about a detector panel.

    Attributes:

        cnx: The x coordinate of the corner of the panel in the detector reference
            system.

        cny: The y coordinate of the corner of the panel in the detector reference
            system.

        clen: The perpendicular distance, as reported by the facility, of the sample
            interaction point from the corner of the panel.

        clen_from: The internal path to the `clen` information in an HDF5 data file, in
            case the information is extracted from it.

        coffset: The offset to be applied to the `clen` value reported by the facility
            in order to determine the real perpendicular distance of the panel from the
            interaction point.

        mask: The internal path, in an HDF5 data file, to the mask data for the panel.

        mask_file: The name of the HDF5 data file in which the mask data for the panel
            can be found.

        satmap: The internal path, in an HDF5 data file, to the per-pixel saturation
            map for the panel.

        satmap_file: The name of the HDF5 data file in which the per-pixel saturation
            map for the panel can be found.

        res: The size of the pixels that make up the the panel (in pixels per meter).

        badrow: The readout direction for the panel, for filtering out clusters of
            peaks. The value corresponding to this key must be either `x` or `y`.

        no_index: Wether the panel should be considered entirely bad. The panel will be
            considered bad if the value corresponding to this key is non-zero.

        adu_per_photon: The number of ADUs per photon for the panel.

        max_adu: The ADU value above which a pixel of the panel should be considered
            unreliable.

        data: The internal path, in an HDF5 data file, to the data block where the
            panel data is stored.

        adu_per_eV: The number of ADUs per eV of photon energy for the panel.

        dim_structure: A description of the internal layout of the data block storing
            the panel's data. The value corresponding to this key is a list of strings
            which define the role of each axis in the data block. See the
            [crystfel_geometry](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)
            man page for a detailed explanation.

        fsx: The fs->x component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        fsy: The fs->y component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        fsz: The fs->z component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        ssx: The ss->x component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        ssy: The ss->y component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        ssz: The ss->z component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        rail_x: The x component, in the detector reference system, of the direction of
            the rail along which the detector moves.

        rail_y: The y component, in the detector reference system, of the direction of
            the rail along which the detector moves.

        rail_z: The z component, in the detector reference system, of the direction of
            the rail along which the detector moves.

        clen_for_centering: The perpendicular distance of the origin of the detector
            reference system from the interaction point, as reported by the facility,

        xfs: The x->fs component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        yfs: The y->fs component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        xss: The x->ss component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        yss: The y->ss component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        orig_min_fs: The initial fs index of the panel data in the data block where
            it is stored.

        orig_max_fs: The final (inclusive) fs index of the panel data in the data block
            where it is stored.

        orig_min_ss: The initial ss index of the panel data in the data block where it
            is stored.

        orig_max_ss: The final (inclusive) fs index of the panel data in the data block
            where it is stored.

        w: The width of the panel in pixels.

        h: The height of the panel in pixels.
    """

    cnx: float
    cny: float
    clen: float
    clen_from: str
    coffset: float
    mask: str
    mask_file: str
    satmap: str
    satmap_file: str
    res: float
    badrow: str
    no_index: bool
    adu_per_photon: float
    max_adu: float
    data: str
    adu_per_eV: float
    dim_structure: List[Union[int, str, None]]
    fsx: float
    fsy: float
    fsz: float
    ssx: float
    ssy: float
    ssz: float
    rail_x: float
    rail_y: float
    rail_z: float
    clen_for_centering: float
    xfs: float
    yfs: float
    xss: float
    yss: float
    orig_min_fs: int
    orig_max_fs: int
    orig_min_ss: int
    orig_max_ss: int
    w: int
    h: int


class TypeBadRegion(TypedDict, total=True):
    """
    A dictionary storing information about a bad region of a detector.

    Attributes:

        panel: The name of the panel in which the bad region lies.

        min_x: The initial x coordinate of the bad region in the detector reference
            system.

        max_x: The final x coordinate of the bad region in the detector reference
            system.

        min_y: The initial y coordinate of the bad region in the detector reference
            system.

        max_y: The final y coordinate of the bad region in the detector reference
            system.

        min_fs: The initial fs index of the bad region in the block where the panel
            data is stored.

        max_fs: The final (inclusive) fs index of the bad region in the block where the
            panel data is stored.

        min_ss: The initial ss index of the bad region in the block where the panel
            data is stored.

        max_ss: The final (inclusive) ss index of the bad region in the block where the
            panel data is stored.

        is_fsss: Whether the fs,ss definition of the bad region (as opposed to the
            x,y-based one) should be considered. In the first case, the min_fs, max_fs,
            min_ss, and max_ss entries in this dictionary will define the bad region.
            In the second case, the min_x, max_x, min_y, and max_y entries will. If the
            value corresponding to this key is 1, the fs,ss-based definition will be
            considered valid. Otherwise, the x,y definition will be used.
    """

    panel: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_fs: int
    max_fs: int
    min_ss: int
    max_ss: int
    is_fsss: int


class TypeDetector(TypedDict):
    """
    A dictionary storing information about a detector.

    Attributes:

        panels: The panels in the detector. The value corresponding to this key is
            dictionary containing information about the panels that make up the
            detector. In the dictionary, the keys are the panel names, and the values
            are [`TypePanel`][om.lib.geometry.TypePanel] dictionaries.

        bad: The bad regions in the detector. The value corresponding to this key is a
            dictionary containing information about the bad regions in the detector. In
            the dictionary, the keys are bad region names, and the values are
            [`TypeBadRegion`][om.lib.geometry.TypeBadRegion] dictionaries.

        mask_bad: The value used in a bad pixel mask to label a pixel as bad.

        mask_good: The value used in a bad pixel mask to label a pixel as good.

        rigid_groups: The rigid groups of panels in the detector. The value
            corresponding to this key is a dictionary containing information about the
            rigid groups. In the dictionary, the keys are names of rigid groups and the
            values are lists storing the names of the panels belonging to each group.

        rigid_group_collections: The collections of rigid groups of panels in the
            detector. The value corresponding to this key is a dictionary containing
            information about the rigid group collections. In the dictionary, the keys
            are names of rigid group collections and the values are lists storing the
            names of the rigid groups belonging to the each collection.

        furthest_out_panel: The name of the panel which contains the pixel that is the
            furthest away from the center of the detector reference system.

        furthest_out_fs: The fs coordinate, within its panel, of the pixel that is the
            furthest away from the center of the detector reference system.

        furthest_out_ss: The ss coordinate, within its panel, of the pixel that is the
            furthest away from the center of the detector reference system.

        furthest_in_panel: The name of the panel which contains the closest pixel to
            the center of the detector reference system.

        furthest_in_fs: The fs coordinate, within its panel, of the closest pixel to
            the center of the detector reference system.

        furthest_in_ss: The ss coordinate, within its panel, of the closest pixel to
            the center of the detector reference system.
    """

    panels: Dict[str, TypePanel]
    bad: Dict[str, TypeBadRegion]
    mask_bad: int
    mask_good: int
    rigid_groups: Dict[str, List[str]]
    rigid_group_collections: Dict[str, List[str]]
    furthest_out_panel: str
    furthest_out_fs: float
    furthest_out_ss: float
    furthest_in_panel: str
    furthest_in_fs: float
    furthest_in_ss: float


class TypeDetectorLayoutInformation(TypedDict, total=True):
    """
    Detector layout information for the peakfinder8 algorithm.

    A dictionary storing information about the internal layout of a detector data frame
    for a specific detector. The information is needed by the
    [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
    algorithm, and is usually retrieved via the
    [`get_layout_info`][om.lib.geometry.GeometryInformation.get_layout_info]
    function.

    Attributes:

        asic_nx: The fs size in pixels of each detector panel in the data frame.

        asic_ny: The ss size in pixels of each detector panel in the data frame.

        nasics_x: The number of detector panels along the fs axis of the data frame.

        nasics_y: The number of detector panels along the ss axis of the data frame.
    """

    asic_nx: int
    asic_ny: int
    nasics_x: int
    nasics_y: int


class TypePixelMaps(TypedDict):
    """
    A dictionary storing a set of pixel maps.

    This dictionary stores a set of look-up pixels maps. Each map stores the value of a
    specific coordinate for eac pixel in a detector data frame. All coordinates in this
    set of maps are assumed to be relative to the detector's reference system.

    Attributes:

        x: A pixel map for the x coordinate.

        y: A pixel map for the y coordinate.

        z: A pixel map for the z coordinate.

        radius: A pixel map storing the distance of each pixel from the center of the
            reference system (usually the center of the detector).

        phi: A pixel map storing, for each pixel, the amplitude of the angle drawn by
            the pixel, the center of the reference system, and the x axis.
    """

    x: NDArray[numpy.float_]
    y: NDArray[numpy.float_]
    z: NDArray[numpy.float_]
    radius: NDArray[numpy.float_]
    phi: NDArray[numpy.float_]


class TypeVisualizationPixelMaps(TypedDict):
    """
    A dictionary storing a set of pixel maps used for visualization.

    This dictionary stores a set of look-up pixels maps. Each map stores the value of
    a specific coordinate for each pixel in a detector data frame. This set of pixel
    maps is supposed to be used for visualization: all coordinates are assumed to
    refer to a cartesian reference system mapped on a 2D array storing pixel
    information for an assembled detector image, with the origin in the top left
    corner.

    Attributes:

        x: A pixel map for the x coordinate.

        y: A pixel map for the y coordinate.
    """

    x: NDArray[numpy.int_]
    y: NDArray[numpy.int_]


class TypeClassSumData(TypedDict):
    """
    Cheetah data class sum data.

    A dictionary storing the number of detector frames belonging to a specific data
    class, their sum, and the virtual powder pattern generated from the Bragg peaks
    detected in them.

    Attributes:

        num_frames: The number of detector frames belonging to the data class.

        sum_frames: The sum of the detector frames belonging to the class.

        peak_powder: The virtual powder pattern for the data class.
    """

    num_frames: int
    sum_frames: NDArray[numpy.float_]
    peak_powder: NDArray[numpy.float_]


# class CrystallographyPeakDetectionProtocol(Protocol):
#     """
#     See documentation of the `__init__` function.
#     """

#     def __init__(
#         self,
#         *,
#         data_source_name: str,
#         monitor_parameters: MonitorParameters,
#     ) -> None:
#         """
#         Protocol for Bragg peak detection algorithm.

#         Peak detections algorithms identify Bragg peaks in X-ray diffraction images.

#         This Protocol class describes the interface that every algorithm of this kind
#         in OM must implement, in order to be fully integrated in OM's Serial
#         Crystallography data processing pipeline


#         """


class OmDataSourceProtocol(Protocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Protocol for OM's Data Source classes.

        Data Sources are classes that perform all the operations needed to retrieve
        data from a single specific sensor or detector. A Data Source class can refer
        to any type of detector, from a simple diode or wave digitizer, to a big x-ray
        or optical detector.

        This Protocol class describes the interface that every Data Source class in OM
        must implement.

        A Data Source class must be initialized with the full set of OM's configuration
        parameters, from which it extracts information about the sensor or detector. An
        identifying name for the sensor must also be provided.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization

            monitor_parameters: An object storing OM's configuration parameters.
        """
        ...

    def initialize_data_source(
        self,
    ) -> None:
        """
        Data source initialization.

        This method prepares OM to retrieve data from the sensor or detector, reading
        all the necessary configuration parameters and retrieving any additional
        required external data.
        """
        ...

    def get_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Any:  # noqa: F821
        """
        Data Retrieval.

        This function retrieves all the data generated by the sensor or detector for
        the provided data event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Data from the sensor.
        """
        ...


class OmDataEventHandlerProtocol(Protocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Protocol class for OM's Data Event Handler classes.

        Data Event Handlers are classes that deal with data events and their sources.
        They have methods to initialize data event sources, retrieve events from them,
        open and close events, and examine the events' content.

        This Protocol class describes the interface that every Data Event Handler class
        in OM must implement.

        A Data Event Handler class must be initialized with a string describing its
        data event source, and with a set of Data Source class instances that instruct
        the Data Event Handler on how to retrieve data from the events.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the data source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        ...

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes event handling on the collecting node.

        This function is called on the collecting node when OM starts, and initializes
        the event handling on the node.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes event handling on a processing node.

        This function is called on a processing node when OM starts. It configures the
        node to start retrieving and processing data events, and initializes all the
        relevant Data Sources.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves events from the source.

        This function retrieves a series of data events from a source. OM calls this
        function on each processing node to start retrieving events. The function,
        which is a generator, returns an iterator over the events that the calling node
        must process.

        #TODO: Fix documentation

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including
                all the processing nodes and the collecting node.

        Yields:

            A dictionary storing the data for the current event.
        """
        ...

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a frame stored in an event.

        This function extracts data from a data event. It works by calling, one after
        the other, the `get_data` function of each Data Source associated with the
        event, passing the event itself as input each time. Each function call returns
        the data extracted from the Data Source. All the retrieved data items are
        finally aggregated and returned.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                  data has been retrieved.

                * The corresponding dictionary value stores the data that could be
                  extracted from the Data Source for the provided event.
        """
        ...

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes frame data retrieval.

        This function initializes the retrieval of data for a single standalone data
        event from a data event source, with all its related information. The way this
        function operates is in contrast with the way OM usually works. OM usually
        retrieves a series of events in sequence, one after the other. This function
        retrieves a single event, separated from all others.

        This function can be called on any type of node in OM and even outside of an
        OnDA Monitor class instance. It prepares the system to retrieve the event data,
        it initializes the relevant Data Sources, etc.

        After this function has been called, data for single events can be retrieved by
        invoking the
        [`retrieve_event_data`][om.protocols.data_retrieval_layer.OmDataEventHandlerProtocol.retrieve_event_data]
        function.
        """
        ...

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data attached to the requested data event.

        This function retrieves all the information associated with the data event
        specified by the provided identifier. The data is returned in the form of a
        dictionary.

        Before this function can be called, frame data retrieval must be initialized by
        calling the
        [`initialize_event_data_retrieval`][om.protocols.data_retrieval_layer.OmDataEventHandlerProtocol.initialize_event_data_retrieval]
        function.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested data event.
        """
        ...


class OmDataRetrievalProtocol(Protocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        monitor_parameters: MonitorParameters,
        source: str,
    ) -> None:
        """
        Protocol for OM's Data Retrieval classes.

        Data Retrieval classes implement OM's Data Retrieval Layer for a specific
        beamline, experiment or facility. They describe how data is retrieved and
        data events are managed.

        This Protocol class describes the interface that every Data Retrieval class in
        OM must implement.

        A Data Retrieval class must be initialized with a string describing a data
        event source, and the full set of OM's configuration parameters.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        ...

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the class.

        This function returns the Data Event Handler used by the Data Retrieval class
        to manipulate data events.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        ...


class OmProcessingProtocol(Protocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters) -> None:
        """
        Protocol for OM's Processing classes.

        Processing classes implement scientific data processing pipelines in OM. A
        Processing class defines how each individual retrieved data event is analyzed
        on the processing nodes and how multiple events are aggregated on the
        collecting node. A Processing class also determined which actions OM performs
        at the beginning and at the end of the data processing.

        This Protocol class describes the interface that every Processing class in OM
        must implement.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        ...

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes an OM processing node.

        This function is invoked on each processing node when OM starts. It performs
        all the operations needed to prepares the node to retrieve and process data
        events (recovering additional needed external data, initializing the algorithms
        with all required parameters, etc.)

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes an OM collecting node.

        This function is invoked on the collecting node when OM starts. It performs all
        the operation needed to prepare the collecting node to aggregate events
        received from the processing nodes (creating memory buffers,
        initializing the collecting algorithm, etc.)

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def process_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a single data event.

        This function is invoked on each processing node for every retrieved data
        event. It receives the data event as input and returns processed data. The
        output of this function is transferred by OM to the collecting node.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data retrieved by OM for the data event
                being processed.

                * The dictionary keys must be the names of the Data Sources for which
                  OM retrieves data. The keys in this dictionary must match the Data
                  Source names listed in the `required_data` entry of OM's `om`
                  configuration parameter group.

                * The corresponding dictionary values must store the the data that OM
                  retrieved for each of the Data Sources.

        Returns:

            A tuple with two entries, with the first entry being a dictionary storing
                the processed data that should be sent to the collecting node, and the
                second being the OM rank number of the node that processed the
                information.
        """
        ...

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Performs operations on the collecting node when no data is received.

        This function is called on the collecting node continuously, when the node is
        not receiving data from any processing node (When data is received, the
        [`collect_data`][om.protocols.processing_layer.OmProcessingProtocol.collect_data]
        is invoked instead). This function can be used to perform operations that need
        to be carried out even when the data stream is not active (reacting to external
        commands and requests, updating graphical interfaces, etc.)

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Collects processed data from a processing node.

        This function is invoked on the collecting node every time data is received
        from a processing node (When data is not being received, the collecting node
        continuously calls the
        [`wait_for_data`][om.protocols.processing_layer.OmProcessingProtocol.wait_for_data]
        function instead). The function accepts as input the data received from
        the processing node (the tuple returned by the
        [`process_data`][om.protocols.processing_layer.OmProcessingProtocol.process_data]
        method of this class), and performs calculations that must be carried out on
        aggregated data (computing cumulative statistics, preparing data for external
        programs or visualization, etc.)

        The function usually does not return any value, but can optionally return a
        nested dictionary (a dictionary whose values are other dictionaries). When this
        happens, the data in the dictionary is provided as feedback data to the
        processing nodes. The nested dictionary must have the following format:

        * The keys of the outer dictionary must match the OM rank numbers of the
          processing nodes which receive the feedback data. A key value of 0 can be
          used to send feedback data to all the processing nodes at the same time.

        * The value corresponding to each key of the outer dictionary must in turn be a
          dictionary that stores the feedback data that is sent to the node defined by
          the key.

        * On each processing node, the feedback data dictionary, when received, is
          merged with the `data` argument of the
          [`process_data`][om.protocols.processing_layer.OmProcessingProtocol.process_data]
          function the next time the function is called.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.

        Returns:

            Usually nothing. Optionally, a nested dictionary that can be used to send
                feedback data to the processing nodes.
        """
        ...

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
        """
        Executes end-of-processing actions on a processing node.

        This function is called on each processing node at the end of the data
        processing, immediately before OM stops. It performs clean up and shut down
        operations (closing communication sockets, computing final statistics, etc.).
        This function usually does not return any value, but can optionally return a
        dictionary. If this happens, the dictionary is transferred to the collecting
        node before the processing node shuts down.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information that must be
                sent to the processing node.
        """
        ...

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Executes end-of-processing actions on the collecting node.

        This function is called on the collecting node at the end of the data
        processing, immediately before OM stops. It often performs clean up and shut
        operations (closing communication sockets, computing final statistics, etc.).

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...


class OmParallelizationProtocol(Protocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_retrieval_layer: OmDataRetrievalProtocol,
        processing_layer: OmProcessingProtocol,
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Protocol for OM's Parallelization classes.

        Parallelization classes orchestrate OM's processing and collecting nodes, and
        take care of the communication between them.

        * When OM start, a Parallelization class instance initializes several
          processing nodes, plus a single collecting node. The class then associates an
          instance of a Data Retrieval class (see
          [`OmDataRetrievalProtocol`][om.protocols.data_retrieval_layer.OmDataRetrievalProtocol])  # noqa: E501
          and an instance of a Processing class (see
          [`OmProcessingProtocol`][om.protocols.processing_layer.OmProcessingProtocol])
          with  each node.

        * Each processing node retrieves an event from a data event source by calling
          the relevant Data Retrieval class methods. It then invokes the appropriate
          Processing class methods on the event. Finally, it transfers the processed
          data to the collecting node. The node then retrieves another event, and the
          cycle continues until there are no more data events or OM shuts down.

        * Every time it receives data from a processing node, the collecting node
          invokes the relevant Processing class methods to aggregate the received data.

        * When all events from the source have been processed, all nodes perform some
          final clean-up tasks by calling the appropriate methods of the Processing
          class. All nodes then shut down.

        This Protocol class describes the interface that every Parallelization class in
        OM must implement.

        Arguments:

            data_retrieval_layer: A class instance defining how data and data events are
                retrieved and handled.

            processing_layer: A class instance defining how retrieved data is processed.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        ...

    def start(self) -> None:
        """
        Starts OM.

        This function begins operations on the processing and collecting nodes.

        When this function is called on a processing node, the processing node starts
        retrieving data events and processing them. When instead this function is
        called on the collecting node, the node starts receiving data from the
        processing nodes and aggregating it.
        """
        ...

    def shutdown(self, *, msg: str = "Reason not provided.") -> None:
        """
        Shuts down OM.

        This function stops the processing and collecting nodes.

        When this function is called on a processing node, the processing node
        communicates to the collecting node that it is shutting down, then shuts down.
        When instead this function is called on the collecting node, the collecting
        node tells every processing node to shut down, waits for all the nodes to
        confirm that they have stopped operating, then shuts itself down.

        Arguments:

            msg: Reason for shutting down. Defaults to "Reason not provided".
        """
        ...
