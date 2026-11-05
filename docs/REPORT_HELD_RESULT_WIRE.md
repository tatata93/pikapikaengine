# 保持荷重Result全25項目を取得する

2026-11-06。held::Result全25項目を追加し、診断取得は合計50型312項目。
保持荷重headerの13型98項目を取得対応する。これは構築済み診断の保存範囲で、最上位Report/C API pump、この取得機能のJS/WASM/game接続は後続。

status/reason、失敗位置、snapshot/world_body、加速度/経路/速度の全3軸、初期証明とflag、
全証明済み区画、安全prefix、侵入証拠と窓、全候補ID、全partition/frontier/current/audits、
last_meshとその所属index、集計Work、区画数/最大深さ、全messageを原値のまま保存する。
元の力/質量/重力から値を作り直さず、監査行のWorkを集計に置換しない。
全tailや証拠より後の未照会領域も削らず、候補IDの原順/重複を保持する。
last_meshなしを再queryで埋めず、safe_prefixなしと[0,0]を区別する。

既存Recordのoptional/optional_count/optional_arrayと全array/bytes経路からconst値を辿る。
製品は既存2TUのまま。新しいモデル実行、再構築、動的確保はgetter内に追加しない。
試験は1harnessと試験用旧interval.cppを結合する。到達値の初期化・寿命・不変性とWriter排他使用は呼出側の契約。
全返却Statusとfinish/completeを確認し、不完全なdocumentを成功として公開しない。

fixtureは人工Result15件。外側13optionalの全なし/全あり/各1項目だけありを比較し、任意2項目の78組×4=312有無組合せを確認する。
全8192組合せの実行とは区別する。各外側コンテナは空/3要素の重複列/2要素の逆順列を含む。
入れ子の原値は従来の独立仕様fixtureを再使用する。新oracleはそれぞれの独立参照を使用し、製品コードから期待値を生成しない。
旧C++試験の構築コードは新harnessに原著のまま組み込み、別の数値model libraryをlinkしない。
人工の証拠・計数・enum・有無を実モデルの認証や実消費量と呼ばない。

Native Release/真Debug、全callback停止/例外/再入と4丸めmode取得、旧13fixtureと全run出力を確認する。
独立検査は全scalar byteとkey、本文の各byte、任意項目の除去/null、enum tag、全非空配列の順序/個数を実改変する。
正式記録は`reports/diagnostic-wire-held-result-verification.json`。16header+manifest gateと旧20profile、数値核/owner/SDK/sampleを保持する。
GNU通常/真Debug/全TU O1 ASan-UBSanとNative全byte一致は公開CIで別受入。
次は自由飛行guardの元snapshotと誤差tubeを取得し、全guard/最上位Reportへ進む。


実受入: Release/真Debugの33080byte/全802typed leaf、17本文1808byteが一致。8512停止・例外/4256再入拒否、4丸めmode保持。独立8569byte+3root+212absent→null+112present除去/null+58enum→U32+180全配列改変拒否。16header+manifest gate1受理19拒否。登録72/70のうち各14CTestのみ実行、Node693skip0/構文/Webbuild成功。新GNUは別受入。


改変検査は初回132.984秒の原記録を保持。独立仕様の期待treeを一度だけ作って再使用する変更後、実66.000秒で全728406byteの検査出力が一致。全改変を文法decode・完全typed比較する対象と条件を維持し、新しい最終source hashも保存した。
