#ifndef PoIBridge_h
#define PoIBridge_h

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void process_frame(uint8_t* rgba, int w, int h);
int poi_get_dim();
int poi_get_n_nodes();
float* poi_get_A();
float* poi_get_K();
float* poi_get_Omega();
float* poi_get_nodes_x();
float* poi_get_nodes_y();
float* poi_get_world_voxels();
float poi_get_pose_x();

#ifdef __cplusplus
}
#endif

#endif /* PoIBridge_h */
