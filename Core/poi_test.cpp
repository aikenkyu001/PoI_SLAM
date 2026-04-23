// ============================================================
//  PoI Unit Test (Native C++ version)
// ============================================================

#include <cassert>
#include <cstdio>
#include <vector>
#include <cmath>

#include "poi.cpp"

void test_threshold_otsu() {
    // ヒストグラムが 0 (10個), 128 (10個), 255 (10個) の画像
    std::vector<uint8_t> gray;
    for(int i=0; i<10; i++) gray.push_back(0);
    for(int i=0; i<10; i++) gray.push_back(128);
    for(int i=0; i<10; i++) gray.push_back(255);
    
    int th = otsu_threshold(gray);
    printf("DEBUG: Otsu threshold = %d\n", th);

    std::vector<uint8_t> bin;
    threshold_otsu(gray, 1, 30, bin);

    // bin[i] = (gray[i] < th) ? 1 : 0;
    // th が 128 前後なら、0 は 1 (前景) に、255 は 0 (背景) になるはず
    assert(bin[0] == 1);
    assert(bin[29] == 0);

    printf("[OK] threshold_otsu\n");
}

void test_skeletonize() {
    std::vector<uint8_t> bin(25, 0);
    for(int x=0; x<5; x++) bin[2*5 + x] = 1;
    for(int y=0; y<5; y++) bin[y*5 + 2] = 1;
    std::vector<uint8_t> skel;
    skeletonize(bin, 5, 5, skel);
    assert(skel[2*5 + 2] == 1);
    printf("[OK] skeletonize\n");
}

void test_graph_distances() {
    std::vector<Edge> edges = {{0,1}, {1,2}};
    std::vector<float> D;
    graph_distances(3, edges, D);
    assert(D[0*3 + 2] == 2.0f);
    printf("[OK] graph_distances\n");
}

void test_A_field() {
    std::vector<Node> nodes = {{0,0,0}, {1,0,1}, {2,0,2}};
    std::vector<float> D = {0,1,2, 1,0,1, 2,1,0};
    std::vector<float> A;
    build_A_field(nodes, D, 3, A);
    assert(A[0*8 + 2] == 1.0f);
    printf("[OK] A-field\n");
}

void test_K_field() {
    std::vector<float> D = {0,1,2, 1,0,1, 2,1,0};
    std::vector<float> K;
    build_K_field(D, 3, 3, K);
    assert(K[0] > 0.99f);
    printf("[OK] K-field\n");
}

void test_motion_estimation_modes() {
    int dim = 3;
    std::vector<float> K1 = {
        1.0f, 0.5f, 0.2f,
        0.5f, 1.0f, 0.5f,
        0.2f, 0.5f, 1.0f
    };
    // 対角成分を少し増やす（前進的な変化をシミュレート）
    std::vector<float> K2 = {
        1.1f, 0.5f, 0.2f,
        0.5f, 1.1f, 0.5f,
        0.2f, 0.5f, 1.1f
    };
    float dx = 0, dy = 0;
    estimate_camera_motion_2d_modes(K1, K2, dim, dx, dy);
    
    // forward = sum(0.1, 0.1, 0.1) = 0.3
    // lateral = sum(0.1, 0.1, 0.1) - sum(0, 0, 0) = 0.3
    // dx = 0.002 * 0.3 = 0.0006
    // dy = 0.002 * 0.3 = 0.0006
    assert(std::abs(dx - 0.0006f) < 1e-6f);
    assert(std::abs(dy - 0.0006f) < 1e-6f);
    printf("[OK] motion_estimation_modes\n");
}

int main() {
    test_threshold_otsu();
    test_skeletonize();
    test_graph_distances();
    test_A_field();
    test_K_field();
    test_motion_estimation_modes();
    printf("=====================================\n");
    printf(" All PoI C++ unit tests passed.\n");
    printf("=====================================\n");
    return 0;
}
