cmake_minimum_required(VERSION 3.1)
project(fastDiffractionImageProcessing)
 
# Set a default build type if none was specified
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Setting build type to 'Release' as none was specified.")
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
    # Set the possible values of build type for cmake-gui
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release"
        "MinSizeRel" "RelWithDebInfo")
endif()
 
include_directories(include)

set(SOURCES src/peakList.cpp
            src/detectorGeometry.cpp
            src/mask.cpp
            src/matlabLikeFunctions.cpp
            src/peakFinder9.cpp
            src/radialBackgroundSubtraction.cpp
            src/streakFinder.cpp
            
            src/adaptions/crystfel/mask.cpp
            src/adaptions/crystfel/peakFinder9.cpp
            
            src/adaptions/cheetah/cheetahConversion.cpp 
            
            src/adaptions/onda/radialBackgroundSubtraction_wrapper.cpp
            src/adaptions/onda/streakFinder_wrapper.cpp
            )
 

add_library(fastDiffractionImageProcessing SHARED ${SOURCES})

set_target_properties(fastDiffractionImageProcessing PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS ON
)

find_package(Eigen3 3.3 NO_MODULE)
if(EIGEN3_FOUND)
    target_link_libraries (fastDiffractionImageProcessing Eigen3::Eigen)
else()
    message("Eigen not found, using internal Eigen.")
    include_directories(SYSTEM include/Eigen)
    
    install(
        DIRECTORY include/Eigen
        DESTINATION include
    )
endif()

install(TARGETS fastDiffractionImageProcessing 
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION lib
)

install(
    DIRECTORY include
    DESTINATION include
    FILES_MATCHING
    PATTERN "*.h"
    PATTERN "Eigen/*" EXCLUDE
    PATTERN "matlabLikeFunctions.h" EXCLUDE
    PATTERN "sortingByOtherValues.h" EXCLUDE
)

