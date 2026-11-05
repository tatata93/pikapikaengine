# World predicateの浮動小数点境界

2026-11-04実読。**公式資料と現設定の読取監査だけ。新ビルド・逆アセンブル・全World/全targetの検証は未実施**。既存source/flags/SDKは変更していない。

**公式の区別。** MSVCのpreciseは結果を変える再結合を抑え、既定FP環境を仮定する。VS2022以降の既定では収縮を生成しないが、旧版は異なり、`/fp:contract` はFMA収縮を許す。strictは環境のアクセス/変更に対応し、収縮を生成しない。中間値の機械精度という注意もあり、strictという名前だけで全targetの各nodeをbinary64と断定しない。[Microsoft `/fp`（実読）](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170)

GCCは `-ffp-contract=off` で収縮を止める。現行資料のC++既定はfastで、native FMAの有無はtargetにも依存する。再結合は別の `-fassociative-math` に属し、fast-mathはunsafe optimizations等も有効にする。`-fno-fast-math` だけからcontract=offを導かない。excess precisionは別条件であり、rounding-mathにも完全保証ではないという注意がある。[GCC Optimize Options（実読：contract / associative / fast / excess precision / rounding）](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)

**現物。** [core.cpp:25](../core/src/core.cpp) のdotは `x*b.x+y*b.y+z*b.z`、ASTは `((x*b.x)+(y*b.y))+(z*b.z)`。`n.dot(p)-offset` はその返却値からの減算である。現CMakeのcore targetはMSVC `/fp:precise`、GNUは警告指定のみ（[CMakeLists.txt](../CMakeLists.txt)）。core.cppはstrict source listに入っていない。生成済み `build/native/pikapika_core.vcxproj` のRelease x64もPrecise、core.cpp固有override無し。記録compilerはMSVC19.51.36247.0。これは**設定の確認**であり、実機命令・環境変数・将来のLTO/pragma変更までの証明ではない。WebAssemblyや別GCC版の生成命令も今回未検査。

**固定ASTの独自導出。** 各 `+ / − / ×` nodeについて、子の全値族からの厳密実数演算結果と、そのbinary64 RN-even結果の**両方を包含**する箱を構成する。ASTを保存するFMAは、積nodeの丸めを省いてexactとし、和nodeで一回RNする場合として帰納的に含まれる。各収縮部分木の内部exact・根RNでも同じ議論になる。したがって、固定順序での通常演算とそのFMA収縮を両方囲む設計は可能である。ただし元kernelの無収縮時とのbit一致を意味しない。

この導出は**再結合・分配・逆数置換、FTZ/DAZ、別丸め、excess precision、overflow/NaNの独自簡約、全World solver**へ拡張しない。新plane-box helperが既存dotを呼ばず同ASTをIntervalで囲む場合も、対応域、各nodeの包含、RN/gradual環境、比較両辺の誤差を別途証明・試験する必要がある。有限テストや公式flag説明だけでこの接続を受入済みとはしない。
