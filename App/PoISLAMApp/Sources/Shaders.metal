#include <metal_stdlib>
using namespace metal;

struct VertexOut {
    float4 position [[position]];
    float4 color;
    float pointSize [[point_size]];
    float2 texCoord;
};

struct NodeVertex {
    float4 position;
    float4 color;
};

// --- Grid Shader (Spatial Nodes) ---
vertex VertexOut grid_vertex(uint vid [[vertex_id]],
                             constant NodeVertex *nodes [[buffer(0)]]) {
    VertexOut out;
    out.position = nodes[vid].position;
    out.color = nodes[vid].color;
    out.pointSize = 5.0; // サイズをシェーダ側で固定（巨大化を防止）
    return out;
}

fragment float4 grid_frag(VertexOut in [[stage_in]]) {
    return in.color;
}

// --- Background Shader ---
struct BGVertexOut {
    float4 position [[position]];
    float2 texCoord;
};

vertex BGVertexOut bg_vertex(uint vid [[vertex_id]]) {
    const float2 pos[4] = { {-1, 1}, {1, 1}, {-1, -1}, {1, -1} };
    const float2 tex[4] = { {0, 0}, {1, 0}, {0, 1}, {1, 1} };
    
    BGVertexOut out;
    out.position = float4(pos[vid], 0.0, 1.0);
    out.texCoord = tex[vid];
    return out;
}

fragment float4 bg_frag(BGVertexOut in [[stage_in]],
                        texture2d<float> tex [[texture(0)]]) {
    constexpr sampler s(mag_filter::linear, min_filter::linear);
    float4 c = tex.sample(s, in.texCoord);
    return float4(c.rgb * 0.5, 1.0); // 背景なので少し暗くする
}
