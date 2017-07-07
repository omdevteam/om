/*
 * eigenSTLContainers.h
 *
 *  Created on: 21.12.2016
 *      Author: Yaro
 */

#ifndef EIGENSTLCONTAINERS_H_
#define EIGENSTLCONTAINERS_H_

#include <Eigen/Dense>
#include <Eigen/StdVector>

#include <vector>

#include "detectorGeometry.h"

namespace EigenSTL
{
typedef std::vector< Eigen::Vector2f, Eigen::aligned_allocator< Eigen::Vector2f > > vector_Vector2f;
typedef std::vector< Eigen::Vector2d, Eigen::aligned_allocator< Eigen::Vector2d > > vector_Vector2d;
typedef std::vector< Eigen::Vector3f, Eigen::aligned_allocator< Eigen::Vector3f > > vector_Vector3f;
typedef std::vector< Eigen::Vector3d, Eigen::aligned_allocator< Eigen::Vector3d > > vector_Vector3d;
typedef std::vector< Eigen::Vector4f, Eigen::aligned_allocator< Eigen::Vector4f > > vector_Vector4f;

typedef std::vector< std::vector< std::vector< Eigen::Vector2f, Eigen::aligned_allocator< Eigen::Vector2f > > > > vector3_Vector2f;

typedef std::vector< detectorPosition_t, Eigen::aligned_allocator< detectorPosition_t > > vector_detectorPosition_t;
}

#endif /* EIGENSTLCONTAINERS_H_ */
