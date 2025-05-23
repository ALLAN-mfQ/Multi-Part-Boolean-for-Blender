# Multi Part Boolean　-for-Blender-


## 概要

マルチパート・ブーリアンは、複数の独立したメッシュが重なった構造のオブジェクトを分割して処理することで、複雑なブーリアン演算を一発で実行するために設計されたBlenderアドオンです。  
結果は実行ごとに新規作成されたコレクションに生成され、元のオブジェクトには影響しません。  
例えばフィギュアの髪の毛パーツ等、独立した毛束の集合体で出来ているようなオブジェクトをメッシュの独立を維持したまま一発でブーリアン出来ます。  
Blenderの標準ブーリアンでは穴が塞がらなかったり、"自分自身と交差"をしたくない場合に使用します。  

https://github.com/user-attachments/assets/d1baf137-dc0c-4561-b100-fb0221a7138c

## 特徴

*   **対応ブーリアン演算:**
    *   **差分:** ベースパーツからカッターパーツを切り抜きます。
    *   **交差:** ベースパーツとカッターパーツの共通部分を保持します。
*   **ワンクリック一括処理:** オブジェクトの分割からモディファイアの適用、結果の統合まで、ワークフロー全体が一つのオペレータで処理されます。
*   **整理された出力:** 実行ごとに結果オブジェクト用の新しいコレクションが作成されるため、シーンの散乱を防ぎ、イテレーションの管理が容易になります。
*   **国際化対応:** UIは英語と日本語に対応しています。

## インストール方法

1.  zipファイルをダウンロードします。
2.  Blenderを開きます。
3.  `編集 > プリファレンス > アドオン` に移動します。
4.  `インストール...` をクリックし、ダウンロードした`.zip` ファイルを選択し、`アドオンをインストール` をクリックします。
5.  アドオンリストで「Multi-Part Boolean」を検索し、名前の横にあるチェックボックスをオンにして有効化します。

## ツールの場所
 *   3D View > SideBar > マルチパート・ブーリアン
    
## 使用方法

1.  **オブジェクトの選択:**
    *   2つのオブジェクトを選択します。
    *   **アクティブオブジェクト**（最後に選択され、明るいオレンジ色でハイライトされているオブジェクト）が**ベース**オブジェクトとして扱われます。
2.  **設定の構成:**
    *   **演算:** 実行したいブーリアン演算を選択します:
        *   `差分`
        *   `交差`
3.  **実行:**
    *   **「ブーリアン処理を一括実行」** ボタンをクリックします。
4.  **結果:**
    *   実行毎に新しいコレクション（例: `MultiPartBoolean_Result_001`）が作成され、結果が生成されます。

## 既知の問題 / 制限事項

*   **パフォーマンス:** 非常に多数のルーズパーツを持つメッシュの場合、処理は計算負荷が高く、かなりの時間がかかることがあります。これは `（ベースパーツ数）×（カッターパーツ数）` のブーリアンモディファイアを生成するためです。
*   **複雑なジオメトリ:** Blenderの他のブーリアン演算と同様に、非常に複雑なジオメトリやノンマニフォールドなジオメトリは、ブーリアンソルバーで予期しない結果やエラーを引き起こす可能性があります。ベースとカッターのメッシュを比較的クリーンな状態に保つことをお勧めします。



## ライセンス
Multi-Part Boolean は **GNU General Public License v3 (GPLv3)** の下で公開されています。このアドオンは自由に使用、改変、配布できますが、派生作品も同じライセンスで公開する必要があります。詳細は [LICENSE](LICENSE) ファイルを参照してください。  


## 著者

- **ALLAN-mfQ　（キュー）**  
- [X](https://x.com/Qdegozaimasu)  
- [Youtube](https://www.youtube.com/channel/UCiIz3zCHwNroYE9h4h5BDew)

