<?xml version="1.0" encoding="UTF-8"?>
<conceptualSchema version="TJ1.0">
    <databaseConnection>
        <embed url="/E:/_3_Master/Applied-Computational-Intelligence-UBB/Year1_Semester2_KnowledgeDiscovery/FinalProject/ToscanaJScalesProject/Final_Processed_Steel_Data_Clean_Full.sql" />
        <table name="PREPROCESSEDDATASET" />
        <key name="DATETIME_COMBINED" />
    </databaseConnection>
    <queries />
    <diagram title="NominalScale_RULClass">
        <node id="0">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (PREPROCESSEDDATASET.RUL_CLASS = 'Medium') AND NOT (PREPROCESSEDDATASET.RUL_CLASS = 'Low') AND NOT (PREPROCESSEDDATASET.RUL_CLASS = 'Healthy') AND NOT (PREPROCESSEDDATASET.RUL_CLASS = 'Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-232.01885533332825" y="135.12922286987305" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.RUL_CLASS = 'Critical'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Critical</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-120.1382668018341" y="173.83574295043945" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.RUL_CLASS = 'Low'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Low</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="157.86156916618347" y="218.35242080688477" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.RUL_CLASS = 'Healthy'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Healthy</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="17.36304545402527" y="194.89011764526367" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.RUL_CLASS = 'Medium'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Medium</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-106.25623321533203" y="327.08367919921875" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="0" to="1" />
        <edge from="0" to="2" />
        <edge from="0" to="3" />
        <edge from="0" to="4" />
        <edge from="1" to="5" />
        <edge from="2" to="5" />
        <edge from="3" to="5" />
        <edge from="4" to="5" />
        <projectionBase>
            <vector x="80.5" y="82.5" />
            <vector x="33.0" y="50.0" />
            <vector x="-17.0" y="60.0" />
            <vector x="-147.0" y="170.0" />
        </projectionBase>
    </diagram>
    <diagram title="NominalScale_SteelType">
        <node id="0">
            <position x="-13.72717406916803" y="389.00310431117833" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = '1015'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>1015</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="357.5459930909053" y="484.8546513573564" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = '1018'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>1018</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-466.36154633774345" y="255.83634555828036" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = '25G2S'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>25G2S</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="135.32846069335938" y="194.7339630126953" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (PREPROCESSEDDATASET.STEEL_TYPE = 'YP') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = 'V500V') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = 'St4sp') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = 'St3sp') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = 'Arm500') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = 'Arm240') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = '25G2S') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = '20') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = '1018') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = '1015') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = '1010') AND NOT (PREPROCESSEDDATASET.STEEL_TYPE = '1008')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="430.3446711958486" y="516.4007255776901" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = '1010'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>1010</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="152.4964288873123" y="431.46896716382565" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = 'Arm500'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Arm500</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="628.1340777729212" y="561.7854357543545" />
            <attributeLabelStyle>
                <offset x="-0.8067855834960938" y="36.92375659942627" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = 'St3sp'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>St3sp</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="-329.1880532396401" y="296.79146500339175" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = 'V500V'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>V500V</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="265.3343537831188" y="453.3085771370225" />
            <attributeLabelStyle>
                <offset x="51.72908020019531" y="20.37812304496765" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = 'YP'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>YP</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="-106.59825134277344" y="635.46044921875" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="65.1380421459502" y="407.2027411288446" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = '1008'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>1008</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="-104.72550330177678" y="361.096937829236" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = '20'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>20</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="503.1433165922224" y="540.6669516126709" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = 'Arm240'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Arm240</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="-212.71018789687253" y="329.5508636089024" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.STEEL_TYPE = 'St4sp'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>St4sp</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="3" to="0" />
        <edge from="3" to="1" />
        <edge from="3" to="2" />
        <edge from="3" to="4" />
        <edge from="3" to="5" />
        <edge from="3" to="6" />
        <edge from="3" to="7" />
        <edge from="3" to="8" />
        <edge from="0" to="9" />
        <edge from="1" to="9" />
        <edge from="2" to="9" />
        <edge from="4" to="9" />
        <edge from="5" to="9" />
        <edge from="6" to="9" />
        <edge from="7" to="9" />
        <edge from="8" to="9" />
        <edge from="10" to="9" />
        <edge from="11" to="9" />
        <edge from="12" to="9" />
        <edge from="13" to="9" />
        <edge from="3" to="10" />
        <edge from="3" to="11" />
        <edge from="3" to="12" />
        <edge from="3" to="13" />
        <projectionBase>
            <vector x="80.01168060302734" y="80.00003814697266" />
            <vector x="40.011566162109375" y="40.000152587890625" />
            <vector x="20.0111083984375" y="20.0006103515625" />
            <vector x="10.00927734375" y="10.00244140625" />
            <vector x="5.001953125" y="5.009765625" />
            <vector x="2.47265625" y="2.5390625" />
            <vector x="1.10546875" y="1.40625" />
            <vector x="0.01171875" y="1.25" />
            <vector x="-2.17578125" y="2.8125" />
            <vector x="-9.83203125" y="10.15625" />
            <vector x="-39.91015625" y="40.078125" />
            <vector x="-159.94921875" y="160.0390625" />
        </projectionBase>
    </diagram>
    <diagram title="NominalScale_WorkpieceGeometry">
        <node id="0">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (PREPROCESSEDDATASET.WORKPIECE_SLICE_GEOMETRY = '180x180') AND NOT (PREPROCESSEDDATASET.WORKPIECE_SLICE_GEOMETRY = '150x150')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.WORKPIECE_SLICE_GEOMETRY = '180x180'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>180x180</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-56.0" y="320.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-108.0" y="200.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.WORKPIECE_SLICE_GEOMETRY = '150x150'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>150x150</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="0" to="1" />
        <edge from="1" to="2" />
        <edge from="3" to="2" />
        <edge from="0" to="3" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="NominalScale_AlloyType">
        <node id="0">
            <position x="-108.0" y="200.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.ALLOY_TYPE = 'close'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>close</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-56.0" y="320.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (PREPROCESSEDDATASET.ALLOY_TYPE = 'close') AND NOT (PREPROCESSEDDATASET.ALLOY_TYPE = 'open')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.ALLOY_TYPE = 'open'</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>open</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="2" to="0" />
        <edge from="0" to="1" />
        <edge from="3" to="1" />
        <edge from="2" to="3" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="NominalScale_StreamIdentifier">
        <node id="0">
            <position x="209.52755737304688" y="-2.222931385040283" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (PREPROCESSEDDATASET.NUM_STREAM = 6) AND NOT (PREPROCESSEDDATASET.NUM_STREAM = 5) AND NOT (PREPROCESSEDDATASET.NUM_STREAM = 4) AND NOT (PREPROCESSEDDATASET.NUM_STREAM = 3) AND NOT (PREPROCESSEDDATASET.NUM_STREAM = 2) AND NOT (PREPROCESSEDDATASET.NUM_STREAM = 1)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="30.96756935119629" y="275.843505859375" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-57.22831344604492" y="72.36717224121094" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.NUM_STREAM = 1</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="155.4969482421875" y="146.3585662841797" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.NUM_STREAM = 4</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>4</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="10.751280784606934" y="98.26416015625" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.NUM_STREAM = 2</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="79.65576934814453" y="119.99913787841797" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.NUM_STREAM = 3</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>3</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="313.4892883300781" y="198.1525421142578" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.NUM_STREAM = 6</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>6</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="222.38739013671875" y="172.25555419921875" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>PREPROCESSEDDATASET.NUM_STREAM = 5</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>5</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="2" to="1" />
        <edge from="3" to="1" />
        <edge from="4" to="1" />
        <edge from="5" to="1" />
        <edge from="6" to="1" />
        <edge from="7" to="1" />
        <edge from="0" to="2" />
        <edge from="0" to="3" />
        <edge from="0" to="4" />
        <edge from="0" to="5" />
        <edge from="0" to="6" />
        <edge from="0" to="7" />
        <projectionBase>
            <vector x="80.59375" y="80.15625" />
            <vector x="40.125" y="40.625" />
            <vector x="18.25" y="22.5" />
            <vector x="0.75" y="20.0" />
            <vector x="-34.25" y="45.0" />
            <vector x="-156.75" y="162.5" />
        </projectionBase>
    </diagram>
    <diagram title="OrdinalScale_ExcludeBounds_CastInRow">
        <node id="0">
            <position x="-5.710253715515137" y="245.05734252929688" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="1">(CAST_IN_ROW&gt;8) AND (CAST_IN_ROW&lt;=16)</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="1">&gt;8</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="174.23533630371094" y="263.1672058105469" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="0">(CAST_IN_ROW&gt;16)</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="0">&gt;16</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-185.36146545410156" y="224.24923706054688" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="2">(CAST_IN_ROW&lt;=8)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="2" to="0" />
        <edge from="0" to="1" />
        <projectionBase>
            <vector x="-56.0" y="240.0" />
            <vector x="-56.0" y="240.0" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_RULEncoded_x_SteelTemperature">
        <node id="0">
            <position x="703.9184977213545" y="317.8191150029504" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="5">((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="9">((RUL_CLASS_ENCODED&lt;=0)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="2">STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="11">((RUL_CLASS_ENCODED&lt;=0)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="4">STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="8">((RUL_CLASS_ENCODED&lt;=0)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="651.9184977213545" y="197.8191150029504" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="0">((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="1003.8777465820326" y="356.72867250442704" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="3">((RUL_CLASS_ENCODED&gt;2)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="951.8777465820326" y="236.72867250442704" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="4">((RUL_CLASS_ENCODED&gt;2)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="403.9592488606769" y="278.9095575014749" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="7">((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="351.9592488606769" y="158.90955750147492" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="2">((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="299.9592488606769" y="38.90955750147492" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="10">((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="3">RUL_CLASS_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="599.9184977213545" y="77.81911500295041" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="1">((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="0">RUL_CLASS_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="899.8777465820326" y="116.72867250442704" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="6">((RUL_CLASS_ENCODED&gt;2)) AND ((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="1">RUL_CLASS_ENCODED &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="4" to="0" />
        <edge from="7" to="0" />
        <edge from="2" to="1" />
        <edge from="3" to="2" />
        <edge from="8" to="4" />
        <edge from="10" to="4" />
        <edge from="0" to="5" />
        <edge from="6" to="5" />
        <edge from="4" to="6" />
        <edge from="11" to="6" />
        <edge from="1" to="7" />
        <edge from="8" to="7" />
        <edge from="2" to="8" />
        <edge from="9" to="8" />
        <edge from="3" to="9" />
        <edge from="9" to="10" />
        <edge from="10" to="11" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="52.0" y="120.0" />
            <vector x="299.9592488606769" y="38.90955750147492" />
            <vector x="299.9592488606776" y="38.90955750147549" />
            <vector x="299.95924886067814" y="38.90955750147663" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_RULEncoded_x_ResistanceTonn">
        <node id="0">
            <position x="471.4750061035172" y="165.3325500488266" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="10">((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((RESISTANCE_TONN&gt;6280) AND (RESISTANCE_TONN&lt;=12560))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="523.4750061035172" y="285.33255004882653" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="9">((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((RESISTANCE_TONN&gt;12560))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="419.4750061035172" y="45.33255004882659" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="7">((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((RESISTANCE_TONN&lt;=6280))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="3">RUL_CLASS_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="261.73750305175747" y="142.66627502441443" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="0">((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((RESISTANCE_TONN&gt;6280) AND (RESISTANCE_TONN&lt;=12560))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="313.73750305175747" y="262.6662750244144" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="1">((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((RESISTANCE_TONN&gt;12560))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="11">((RUL_CLASS_ENCODED&lt;=0)) AND ((RESISTANCE_TONN&gt;12560))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="4">RESISTANCE_TONN &gt;12560</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="681.2125091552715" y="187.99882507324537" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="3">((RUL_CLASS_ENCODED&gt;2)) AND ((RESISTANCE_TONN&gt;6280) AND (RESISTANCE_TONN&lt;=12560))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="6">((RUL_CLASS_ENCODED&lt;=0)) AND ((RESISTANCE_TONN&gt;6280) AND (RESISTANCE_TONN&lt;=12560))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="2">RESISTANCE_TONN &gt;6280</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="8">((RUL_CLASS_ENCODED&lt;=0)) AND ((RESISTANCE_TONN&lt;=6280))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="733.2125091552715" y="307.99882507324537" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="2">((RUL_CLASS_ENCODED&gt;2)) AND ((RESISTANCE_TONN&gt;12560))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="629.2125091552715" y="67.99882507324537" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="5">((RUL_CLASS_ENCODED&gt;2)) AND ((RESISTANCE_TONN&lt;=6280))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="1">RUL_CLASS_ENCODED &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="209.73750305175747" y="22.666275024414432" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="4">((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((RESISTANCE_TONN&lt;=6280))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="0">RUL_CLASS_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="2" to="0" />
        <edge from="3" to="0" />
        <edge from="0" to="1" />
        <edge from="4" to="1" />
        <edge from="11" to="2" />
        <edge from="7" to="3" />
        <edge from="11" to="3" />
        <edge from="3" to="4" />
        <edge from="5" to="4" />
        <edge from="7" to="5" />
        <edge from="0" to="6" />
        <edge from="10" to="6" />
        <edge from="8" to="7" />
        <edge from="1" to="9" />
        <edge from="6" to="9" />
        <edge from="2" to="10" />
        <edge from="8" to="11" />
        <projectionBase>
            <vector x="209.73750305175975" y="22.66627502441216" />
            <vector x="52.0" y="120.0" />
            <vector x="52.0" y="120.0" />
            <vector x="209.7375030517543" y="22.66627502441878" />
            <vector x="209.73750305175747" y="22.666275024414432" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_SteelTemperature_x_WaterCooling">
        <node id="0">
            <position x="785.1890869140625" y="79.2476806640625" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="837.1890869140625" y="199.2476806640625" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&gt;0) AND (WATER_CONSUMPTION_LITER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="496.59454345703125" y="279.62384033203125" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="889.1890869140625" y="319.2476806640625" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;1)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>WATER_CONSUMPTION_LITER_MINUTE_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="444.59454345703125" y="159.62384033203125" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&gt;0) AND (WATER_CONSUMPTION_LITER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=0)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&gt;0) AND (WATER_CONSUMPTION_LITER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>WATER_CONSUMPTION_LITER_MINUTE_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="392.59454345703125" y="39.62384033203125" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&gt;0) AND (STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED&lt;=1)) AND ((WATER_CONSUMPTION_LITER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="8" to="0" />
        <edge from="0" to="1" />
        <edge from="5" to="1" />
        <edge from="4" to="2" />
        <edge from="5" to="2" />
        <edge from="1" to="3" />
        <edge from="2" to="3" />
        <edge from="7" to="4" />
        <edge from="7" to="5" />
        <edge from="8" to="5" />
        <edge from="6" to="7" />
        <edge from="6" to="8" />
        <projectionBase>
            <vector x="392.59454345703125" y="39.62384033203125" />
            <vector x="52.0" y="120.0" />
            <vector x="52.0" y="120.0" />
            <vector x="392.59454345703125" y="39.62384033203125" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_CrystalizerMovement_x_SwingFrequency">
        <node id="0">
            <position x="474.60327911376953" y="165.34825134277344" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&gt;0) AND (CRYSTALLIZER_MOVEMENT_MM_ENCODED&lt;=1)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&gt;0) AND (SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="897.2065582275391" y="210.69650268554688" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&gt;1)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&gt;0) AND (SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="949.2065582275391" y="330.6965026855469" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&gt;1)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="845.2065582275391" y="90.69650268554688" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&gt;1)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>CRYSTALLIZER_MOVEMENT_MM_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&lt;=0)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&gt;0) AND (SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="422.60327911376953" y="45.34825134277344" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&gt;0) AND (CRYSTALLIZER_MOVEMENT_MM_ENCODED&lt;=1)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>CRYSTALLIZER_MOVEMENT_MM_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&lt;=0)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="526.6032791137695" y="285.34825134277344" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&gt;0) AND (CRYSTALLIZER_MOVEMENT_MM_ENCODED&lt;=1)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((CRYSTALLIZER_MOVEMENT_MM_ENCODED&lt;=0)) AND ((SWING_FREQUENCY_AMOUNT_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="4" to="0" />
        <edge from="5" to="0" />
        <edge from="0" to="1" />
        <edge from="3" to="1" />
        <edge from="1" to="2" />
        <edge from="7" to="2" />
        <edge from="5" to="3" />
        <edge from="8" to="4" />
        <edge from="8" to="5" />
        <edge from="4" to="6" />
        <edge from="0" to="7" />
        <edge from="6" to="7" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_RULEncoded_x_Stream">
        <node id="0">
            <position x="2421.5735473632885" y="493.6065368652204" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&gt;5))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="2064.591359456365" y="666.2966054280553" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&gt;4) AND (NUM_STREAM&lt;=5))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="39.95434570312504" y="218.53527832031287" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="1627.7004801432238" y="401.9161173502579" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&gt;3) AND (NUM_STREAM&lt;=4))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="1230.7639465331913" y="356.07090759277673" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&gt;2) AND (NUM_STREAM&lt;=3))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="873.7817586262978" y="528.7609761556009" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&gt;1) AND (NUM_STREAM&lt;=2))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="2501.482238769539" y="930.677093505847" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&gt;5))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="1984.6826680501147" y="229.2260487874289" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&gt;4) AND (NUM_STREAM&lt;=5))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_STREAM &gt;4</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="1190.809600830066" y="137.5356292724639" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&gt;2) AND (NUM_STREAM&lt;=3))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_STREAM &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="2381.6192016601626" y="275.07125854490755" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&gt;5))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_STREAM &gt;5</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="2024.6370137532397" y="447.76132710774175" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&gt;4) AND (NUM_STREAM&lt;=5))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="2461.527893066414" y="712.1418151855339" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&gt;5))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="913.7361043294234" y="747.296254475914" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&gt;1) AND (NUM_STREAM&lt;=2))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="476.84522501627697" y="482.9157663981139" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&gt;0) AND (NUM_STREAM&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="1707.6091715494745" y="838.9866739908845" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&gt;3) AND (NUM_STREAM&lt;=4))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="516.7995707194026" y="701.4510447184269" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&gt;0) AND (NUM_STREAM&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="16">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&lt;=0))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="17">
            <position x="833.8274129231725" y="310.2256978352874" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&gt;1) AND (NUM_STREAM&lt;=2))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="18">
            <position x="396.9365336100266" y="45.84520975748751" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&gt;0) AND (NUM_STREAM&lt;=1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_STREAM &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="19">
            <position x="1667.654825846349" y="620.4513956705714" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&gt;3) AND (NUM_STREAM&lt;=4))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="20">
            <position x="119.86303710937598" y="655.6058349609394" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="21">
            <position x="2104.545705159491" y="884.8318837483683" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&gt;4) AND (NUM_STREAM&lt;=5))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="22">
            <position x="436.89087931315163" y="264.38048807780035" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_STREAM&gt;0) AND (NUM_STREAM&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="23">
            <position x="1310.672637939442" y="793.1414642334033" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_STREAM&gt;2) AND (NUM_STREAM&lt;=3))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="24">
            <position x="1270.7182922363165" y="574.6061859130903" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&gt;2) AND (NUM_STREAM&lt;=3))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="25">
            <position x="793.8730672200473" y="91.69041951497456" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&gt;1) AND (NUM_STREAM&lt;=2))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_STREAM &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="26">
            <position x="1587.7461344400986" y="183.38083902994504" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_STREAM&gt;3) AND (NUM_STREAM&lt;=4))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_STREAM &gt;3</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="27">
            <position x="79.90869140625037" y="437.07055664062636" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_STREAM&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="9" to="0" />
        <edge from="10" to="0" />
        <edge from="19" to="1" />
        <edge from="10" to="1" />
        <edge from="16" to="2" />
        <edge from="4" to="3" />
        <edge from="26" to="3" />
        <edge from="17" to="4" />
        <edge from="8" to="4" />
        <edge from="13" to="5" />
        <edge from="17" to="5" />
        <edge from="11" to="6" />
        <edge from="21" to="6" />
        <edge from="26" to="7" />
        <edge from="25" to="8" />
        <edge from="7" to="9" />
        <edge from="3" to="10" />
        <edge from="7" to="10" />
        <edge from="0" to="11" />
        <edge from="1" to="11" />
        <edge from="15" to="12" />
        <edge from="5" to="12" />
        <edge from="22" to="13" />
        <edge from="27" to="13" />
        <edge from="19" to="14" />
        <edge from="23" to="14" />
        <edge from="13" to="15" />
        <edge from="20" to="15" />
        <edge from="22" to="17" />
        <edge from="25" to="17" />
        <edge from="16" to="18" />
        <edge from="3" to="19" />
        <edge from="24" to="19" />
        <edge from="27" to="20" />
        <edge from="1" to="21" />
        <edge from="14" to="21" />
        <edge from="2" to="22" />
        <edge from="18" to="22" />
        <edge from="12" to="23" />
        <edge from="24" to="23" />
        <edge from="4" to="24" />
        <edge from="5" to="24" />
        <edge from="18" to="25" />
        <edge from="8" to="26" />
        <edge from="2" to="27" />
        <projectionBase>
            <vector x="39.95434570312504" y="218.53527832031287" />
            <vector x="396.9365336100159" y="45.84520975748387" />
            <vector x="396.9365336100187" y="45.84520975748933" />
            <vector x="396.9365336100486" y="45.84520975747864" />
            <vector x="396.9365336100266" y="45.84520975748751" />
            <vector x="39.95434570312561" y="218.53527832031307" />
            <vector x="396.9365336100208" y="45.845209757487055" />
            <vector x="396.9365336100325" y="45.84520975748114" />
            <vector x="39.95434570312533" y="218.5352783203135" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_RULEncoded_x_Crystallizer">
        <node id="0">
            <position x="489.2518717447919" y="355.9114405314133" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_CRYSTALLIZER&gt;16))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="1176.192250569659" y="271.1806716918936" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_CRYSTALLIZER&gt;8) AND (NUM_CRYSTALLIZER&lt;=16))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="745.253051757812" y="74.57996114095033" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_CRYSTALLIZER&lt;=8))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="861.8783976236975" y="393.2014211018883" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_CRYSTALLIZER&gt;16))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="1117.8795776367165" y="111.86994171142499" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_CRYSTALLIZER&lt;=8))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="116.62534586588549" y="318.62145996093795" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_CRYSTALLIZER&gt;16))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_CRYSTALLIZER &gt;16</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="372.6265258789064" y="37.289980570475365" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_CRYSTALLIZER&lt;=8))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="430.9391988118491" y="196.600710550944" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((NUM_CRYSTALLIZER&gt;8) AND (NUM_CRYSTALLIZER&lt;=16))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="1234.504923502602" y="430.49140167236294" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((NUM_CRYSTALLIZER&gt;16))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="803.5657246907547" y="233.89069112141897" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((NUM_CRYSTALLIZER&gt;8) AND (NUM_CRYSTALLIZER&lt;=16))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="58.31267293294269" y="159.31072998046864" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_CRYSTALLIZER&gt;8) AND (NUM_CRYSTALLIZER&lt;=16))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>NUM_CRYSTALLIZER &gt;8</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((NUM_CRYSTALLIZER&lt;=8))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="5" to="0" />
        <edge from="7" to="0" />
        <edge from="4" to="1" />
        <edge from="9" to="1" />
        <edge from="6" to="2" />
        <edge from="0" to="3" />
        <edge from="9" to="3" />
        <edge from="2" to="4" />
        <edge from="10" to="5" />
        <edge from="11" to="6" />
        <edge from="6" to="7" />
        <edge from="10" to="7" />
        <edge from="3" to="8" />
        <edge from="1" to="8" />
        <edge from="2" to="9" />
        <edge from="7" to="9" />
        <edge from="11" to="10" />
        <projectionBase>
            <vector x="372.6265258789056" y="37.28998057047497" />
            <vector x="372.62652587890443" y="37.289980570474654" />
            <vector x="58.3126729329428" y="159.31072998046932" />
            <vector x="372.6265258789064" y="37.289980570475365" />
            <vector x="58.31267293294269" y="159.31072998046864" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_RULEncoded_x_Speed">
        <node id="0">
            <position x="425.5170288085936" y="159.49326070149746" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;0) AND (ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;0) AND (ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>ALLOY_SPEED_METER_MINUTE_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="747.034057617188" y="78.98652140299458" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="477.5170288085936" y="279.49326070149743" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="851.034057617188" y="318.9865214029945" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="1172.5510864257797" y="238.47978210449236" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;0) AND (ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>ALLOY_SPEED_METER_MINUTE_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="373.5170288085936" y="39.49326070149746" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="799.034057617188" y="198.98652140299458" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;0) AND (ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="1224.5510864257797" y="358.4797821044923" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&gt;1))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="1120.5510864257797" y="118.47978210449236" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((ALLOY_SPEED_METER_MINUTE_ENCODED&lt;=0))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="1" to="0" />
        <edge from="8" to="0" />
        <edge from="3" to="1" />
        <edge from="8" to="2" />
        <edge from="0" to="4" />
        <edge from="7" to="4" />
        <edge from="4" to="5" />
        <edge from="9" to="5" />
        <edge from="9" to="6" />
        <edge from="11" to="6" />
        <edge from="1" to="7" />
        <edge from="3" to="8" />
        <edge from="0" to="9" />
        <edge from="2" to="9" />
        <edge from="5" to="10" />
        <edge from="6" to="10" />
        <edge from="2" to="11" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="373.5170288085944" y="39.49326070149712" />
            <vector x="52.0" y="120.0" />
            <vector x="373.5170288085936" y="39.49326070149746" />
            <vector x="373.5170288085917" y="39.493260701497775" />
        </projectionBase>
    </diagram>
    <diagram title="GridScale_RULEncoded_x_CastInRow">
        <node id="0">
            <position x="306.9596659342449" y="30.916689554850223" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((CAST_IN_ROW&lt;=20))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;0</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="1024.8789978027341" y="332.75006866455044" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((CAST_IN_ROW&gt;40))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="972.8789978027344" y="212.750068664551" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((CAST_IN_ROW&gt;20) AND (CAST_IN_ROW&lt;=40))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="358.9596659342448" y="150.91668955485034" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((CAST_IN_ROW&gt;20) AND (CAST_IN_ROW&lt;=40))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="665.9193318684897" y="181.83337910970067" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((CAST_IN_ROW&gt;20) AND (CAST_IN_ROW&lt;=40))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="717.9193318684894" y="301.8333791097002" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((CAST_IN_ROW&gt;40))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="613.919331868489" y="61.833379109700616" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;1) AND (RUL_CLASS_ENCODED&lt;=2)) AND ((CAST_IN_ROW&lt;=20))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;1</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((CAST_IN_ROW&gt;20) AND (CAST_IN_ROW&lt;=40))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>CAST_IN_ROW &gt;20</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((CAST_IN_ROW&lt;=20))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="410.9596659342448" y="270.9166895548503" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;0) AND (RUL_CLASS_ENCODED&lt;=1)) AND ((CAST_IN_ROW&gt;40))</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&lt;=0)) AND ((CAST_IN_ROW&gt;40))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>CAST_IN_ROW &gt;40</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="920.8789978027344" y="92.75006866455021" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>((RUL_CLASS_ENCODED&gt;2)) AND ((CAST_IN_ROW&lt;=20))</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>RUL_CLASS_ENCODED &gt;2</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="8" to="0" />
        <edge from="2" to="1" />
        <edge from="5" to="1" />
        <edge from="4" to="2" />
        <edge from="11" to="2" />
        <edge from="0" to="3" />
        <edge from="7" to="3" />
        <edge from="3" to="4" />
        <edge from="6" to="4" />
        <edge from="4" to="5" />
        <edge from="9" to="5" />
        <edge from="0" to="6" />
        <edge from="8" to="7" />
        <edge from="3" to="9" />
        <edge from="10" to="9" />
        <edge from="7" to="10" />
        <edge from="6" to="11" />
        <projectionBase>
            <vector x="-108.0" y="200.0" />
            <vector x="52.0" y="120.0" />
        </projectionBase>
    </diagram>
    <diagram title="Thermal Stability Scale">
        <node id="0">
            <position x="-77.1874303817749" y="402.54559326171875" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT rul_fca_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="38.89396858215332" y="179.00048828125" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT rul_fca_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>temperature_measurement2_celsius_deg_bin</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="175.32046604156494" y="99.82289123535156" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT rul_fca_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>rul_fca_bin</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="98.13303565979004" y="502.3684844970703" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT rul_fca_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="-116.08139896392822" y="223.54510498046875" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT rul_fca_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>temperature_measurement1_celsius_deg_bin</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="59.23906707763672" y="323.3679962158203" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT rul_fca_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="214.21443462371826" y="278.82337951660156" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT rul_fca_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT rul_fca_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement1_celsius_deg_bin FROM PreProcessedDataset) AND  NOT (SELECT temperature_measurement2_celsius_deg_bin FROM PreProcessedDataset)</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="1" to="0" />
        <edge from="4" to="0" />
        <edge from="7" to="1" />
        <edge from="7" to="2" />
        <edge from="0" to="3" />
        <edge from="5" to="3" />
        <edge from="6" to="3" />
        <edge from="7" to="4" />
        <edge from="2" to="5" />
        <edge from="4" to="5" />
        <edge from="1" to="6" />
        <edge from="2" to="6" />
        <projectionBase>
            <vector x="76.0" y="90.0" />
            <vector x="6.0" y="80.0" />
            <vector x="-134.0" y="180.0" />
        </projectionBase>
    </diagram>
    <diagram title="Mechanical Wear">
        <node id="0">
            <position x="96.5" y="192.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-17.0" y="60.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Late Cast</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-131.0" y="280.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="-147.0" y="170.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>High Resistance</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-50.5" y="362.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="63.5" y="142.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="-83.5" y="312.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="-114.0" y="220.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="33.0" y="50.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Heavy Steel</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="-66.5" y="252.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="16.0" y="110.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-164.0" y="230.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="113.5" y="132.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="-33.5" y="302.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="80.5" y="82.5" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE resistance_tonn_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE cast_in_row_bin='High') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_weight_tonn_bin='High') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Critical</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="6" to="0" />
        <edge from="11" to="0" />
        <edge from="13" to="0" />
        <edge from="2" to="1" />
        <edge from="8" to="3" />
        <edge from="11" to="3" />
        <edge from="12" to="3" />
        <edge from="2" to="4" />
        <edge from="0" to="5" />
        <edge from="3" to="5" />
        <edge from="7" to="5" />
        <edge from="14" to="5" />
        <edge from="1" to="6" />
        <edge from="15" to="6" />
        <edge from="6" to="7" />
        <edge from="10" to="7" />
        <edge from="12" to="7" />
        <edge from="9" to="8" />
        <edge from="4" to="8" />
        <edge from="2" to="9" />
        <edge from="15" to="10" />
        <edge from="4" to="10" />
        <edge from="9" to="11" />
        <edge from="1" to="11" />
        <edge from="1" to="12" />
        <edge from="4" to="12" />
        <edge from="9" to="13" />
        <edge from="15" to="13" />
        <edge from="8" to="14" />
        <edge from="10" to="14" />
        <edge from="13" to="14" />
        <edge from="2" to="15" />
        <projectionBase>
            <vector x="80.5" y="82.5" />
            <vector x="33.0" y="50.0" />
            <vector x="-17.0" y="60.0" />
            <vector x="-147.0" y="170.0" />
        </projectionBase>
    </diagram>
    <diagram title="RESISTANCE INTERODINAL SCALE">
        <node id="0">
            <position x="-164.0" y="520.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>RESISTANCE_TONN &gt;= 3000 AND RESISTANCE_TONN &lt; 6000</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-4.0" y="440.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>RESISTANCE_TONN &gt;= 6000 AND RESISTANCE_TONN &lt; 9000</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="104.0" y="240.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 6000</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-216.0" y="400.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 6000</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="-324.0" y="600.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>RESISTANCE_TONN &lt; 3000</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&lt; 3000</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-56.0" y="320.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="-108.0" y="200.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 9000</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="-168.0" y="960.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="52.0" y="120.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 3000</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="156.0" y="360.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>RESISTANCE_TONN &gt;= 9000</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&gt;= 9000</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="3" to="0" />
        <edge from="5" to="0" />
        <edge from="2" to="1" />
        <edge from="5" to="1" />
        <edge from="9" to="2" />
        <edge from="7" to="3" />
        <edge from="3" to="4" />
        <edge from="7" to="5" />
        <edge from="9" to="5" />
        <edge from="6" to="7" />
        <edge from="0" to="8" />
        <edge from="1" to="8" />
        <edge from="4" to="8" />
        <edge from="10" to="8" />
        <edge from="6" to="9" />
        <edge from="2" to="10" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="INTERORDINAL_STEEL_WEIGHT_TONN">
        <node id="0">
            <position x="-77.89387514317423" y="38.0375558749422" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="0">&gt;= 154</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-14.54642763325765" y="57.139154499433744" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-131.5346624090309" y="63.975150853992204" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="0">CAST_IN_ROW &gt;= 175</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="1">&gt;= 175</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="4.144983597838376" y="73.02954645750413" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="1">CAST_IN_ROW &gt;= 136 AND CAST_IN_ROW &lt; 154</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="37.38282246219245" y="31.7807839161419" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="2">&lt; 162</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="11.418197414467329" y="44.45996920778833" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="-103.85850019089673" y="50.7167411665921" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="3">&gt;= 162</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="56.074233693288576" y="47.671175874210235" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="4">&lt; 154</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="18.691411231096097" y="15.89039195807058" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="5">&lt; 175</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="82.57585906982422" y="90.2764663696289" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="2">CAST_IN_ROW &lt; 123</object>
                </objectContingent>
                <attributeContingent>
                    <attribute contextPosition="6">&lt; 123</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="-7.2732138166287825" y="28.56957724971778" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-33.2378388643541" y="41.24876254136501" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="-25.964625047725136" y="12.67918529164939" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="7">&gt;= 123</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="30.109608645563597" y="60.35036116585775" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="66.52078942511616" y="66.30985579614753" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="8">&lt; 136</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="16">
            <position x="-85.16708895980327" y="66.60713312466157" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="3">CAST_IN_ROW &gt;= 162 AND CAST_IN_ROW &lt; 175</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="17">
            <position x="-40.51105268098314" y="69.81833979108262" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="4">CAST_IN_ROW &gt;= 154 AND CAST_IN_ROW &lt; 162</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="18">
            <position x="-59.20246391207837" y="53.92794783301474" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="19">
            <position x="40.55616437739209" y="78.98904108779436" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object contextPosition="5">CAST_IN_ROW &gt;= 123 AND CAST_IN_ROW &lt; 136</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="20">
            <position x="-51.92925009545024" y="25.35837058329537" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute contextPosition="9">&gt;= 136</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="21">
            <position x="-37.07874298095703" y="106.64002227783203" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <edge from="20" to="0" />
        <edge from="12" to="1" />
        <edge from="5" to="1" />
        <edge from="6" to="2" />
        <edge from="1" to="3" />
        <edge from="14" to="3" />
        <edge from="8" to="4" />
        <edge from="10" to="5" />
        <edge from="4" to="5" />
        <edge from="0" to="6" />
        <edge from="4" to="7" />
        <edge from="11" to="8" />
        <edge from="15" to="9" />
        <edge from="13" to="10" />
        <edge from="8" to="10" />
        <edge from="10" to="12" />
        <edge from="20" to="12" />
        <edge from="11" to="13" />
        <edge from="5" to="14" />
        <edge from="7" to="14" />
        <edge from="7" to="15" />
        <edge from="6" to="16" />
        <edge from="18" to="16" />
        <edge from="1" to="17" />
        <edge from="18" to="17" />
        <edge from="0" to="18" />
        <edge from="12" to="18" />
        <edge from="14" to="19" />
        <edge from="15" to="19" />
        <edge from="13" to="20" />
        <edge from="2" to="21" />
        <edge from="3" to="21" />
        <edge from="9" to="21" />
        <edge from="16" to="21" />
        <edge from="17" to="21" />
        <edge from="19" to="21" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="INTERORDINAL_WATER_CONSUMPTION">
        <node id="0">
            <position x="-33.90649777218954" y="91.1672065079357" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-43.21723556518555" y="148.4151611328125" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-132.43000718784708" y="111.80309595355516" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &lt; 1405</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&lt; 1405</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-7.420496334619871" y="68.80658731722394" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="47.66376275737454" y="116.1149203162779" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt;= 2005</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&gt;= 2005</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-26.48600143756954" y="22.3606191907121" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 2005</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="38.13101020589971" y="92.89193625302244" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 1855</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="9.532752551474779" y="23.222984063255325" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 1405</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="-79.45800431270814" y="67.08185757213607" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 1705</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="-52.97200287513874" y="44.72123838142397" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 1855</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="-96.41125319880211" y="112.66546082609966" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt;= 1405 AND WATER_CONSUMPTION_LITER_MINUTE &lt; 1555</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="2.112256216854739" y="92.02957138047861" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-16.95324888609472" y="45.58360325396774" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="-43.439250323664226" y="67.94422244467955" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="19.065505102949544" y="46.44596812651082" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 1555</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="11.64500876832949" y="115.25255544373636" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt;= 1855 AND WATER_CONSUMPTION_LITER_MINUTE &lt; 2005</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="16">
            <position x="-24.373745220714603" y="114.39019057118844" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt;= 1705 AND WATER_CONSUMPTION_LITER_MINUTE &lt; 1855</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="17">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="18">
            <position x="28.59825765442426" y="69.66895218976686" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 1705</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="19">
            <position x="-60.392499209758284" y="113.52782569864416" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt;= 1555 AND WATER_CONSUMPTION_LITER_MINUTE &lt; 1705</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="20">
            <position x="-105.94400575027782" y="89.44247676284317" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 1555</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="21">
            <position x="-69.92525176123323" y="90.30484163538847" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <edge from="3" to="0" />
        <edge from="13" to="0" />
        <edge from="2" to="1" />
        <edge from="4" to="1" />
        <edge from="10" to="1" />
        <edge from="15" to="1" />
        <edge from="16" to="1" />
        <edge from="19" to="1" />
        <edge from="20" to="2" />
        <edge from="12" to="3" />
        <edge from="14" to="3" />
        <edge from="6" to="4" />
        <edge from="17" to="5" />
        <edge from="18" to="6" />
        <edge from="17" to="7" />
        <edge from="9" to="8" />
        <edge from="5" to="9" />
        <edge from="20" to="10" />
        <edge from="21" to="10" />
        <edge from="3" to="11" />
        <edge from="18" to="11" />
        <edge from="5" to="12" />
        <edge from="7" to="12" />
        <edge from="9" to="13" />
        <edge from="12" to="13" />
        <edge from="7" to="14" />
        <edge from="6" to="15" />
        <edge from="11" to="15" />
        <edge from="0" to="16" />
        <edge from="11" to="16" />
        <edge from="14" to="18" />
        <edge from="0" to="19" />
        <edge from="21" to="19" />
        <edge from="8" to="20" />
        <edge from="8" to="21" />
        <edge from="13" to="21" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="INTERORDINAL_STEEL_TEMPERATURE">
        <node id="0">
            <position x="-0.4442886352538773" y="100.92714538574103" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="-59.57733001708999" y="169.20067443847552" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt;= 1116 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt; 1300</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-88.69956207275425" y="102.41029357910173" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 1116</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-15.005404663085933" y="67.53195495605453" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-103.70496673584046" y="169.94224853515664" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt;= 1300 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt; 1483</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="-15.44969329833986" y="168.4591003417969" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt;= 933 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt; 1116</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="28.67794342041003" y="167.7175262451167" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt;= 750 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt; 933</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="14.116827392578045" y="134.32233581542823" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="-147.83260345459013" y="170.68382263183662" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt;= 1483</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&gt;= 1483</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="72.80558013916132" y="166.9759521484366" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt; 750</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&lt; 750</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="-118.26608276367244" y="136.54705810546784" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 1300</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="43.683348083496384" y="100.18557128906195" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 1116</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="-29.566520690917926" y="34.13676452636719" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 750</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="29.122232055664057" y="66.7903808593752" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 1300</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="-34.6966667175293" y="204.66615295410156" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="16">
            <position x="-30.010809326171767" y="135.06390991210856" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="17">
            <position x="-74.13844604492206" y="135.80548400878854" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="18">
            <position x="-59.13304138183628" y="68.27352905273472" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt;= 933</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="19">
            <position x="-44.57192535400418" y="101.6687194824217" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="20">
            <position x="14.561116027831993" y="33.39519042968763" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 1483</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="21">
            <position x="58.24446411132874" y="133.5807617187479" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt; 933</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="3" to="0" />
        <edge from="14" to="0" />
        <edge from="16" to="1" />
        <edge from="17" to="1" />
        <edge from="18" to="2" />
        <edge from="13" to="3" />
        <edge from="20" to="3" />
        <edge from="17" to="5" />
        <edge from="11" to="5" />
        <edge from="8" to="6" />
        <edge from="16" to="6" />
        <edge from="8" to="7" />
        <edge from="21" to="7" />
        <edge from="0" to="8" />
        <edge from="12" to="8" />
        <edge from="11" to="9" />
        <edge from="21" to="10" />
        <edge from="2" to="11" />
        <edge from="14" to="12" />
        <edge from="4" to="13" />
        <edge from="20" to="14" />
        <edge from="1" to="15" />
        <edge from="5" to="15" />
        <edge from="6" to="15" />
        <edge from="7" to="15" />
        <edge from="9" to="15" />
        <edge from="10" to="15" />
        <edge from="0" to="16" />
        <edge from="19" to="16" />
        <edge from="2" to="17" />
        <edge from="19" to="17" />
        <edge from="13" to="18" />
        <edge from="3" to="19" />
        <edge from="18" to="19" />
        <edge from="4" to="20" />
        <edge from="12" to="21" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="INTERORDINAL_STEEL_TEMPERATURE_DECREASING">
        <node id="0">
            <position x="3.020844699928741" y="75.79215991213607" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="17.184252665574867" y="24.813570440126227" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 1483</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-31.34766063122109" y="26.165019031883617" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 750</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="68.73701066229972" y="99.25428176050445" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 933</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="20.20509736550354" y="100.60573035226298" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-14.163407965646137" y="50.9785894720095" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="85.92126332787464" y="124.06785220063091" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt;= 750</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&lt;= 750</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="-40.764137268066406" y="179.88192749023438" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="37.38935003107866" y="125.41930079238807" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt; 750 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt;= 933</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="-45.5110685968676" y="77.14360850389437" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="-108.20638985930759" y="129.47364656765922" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt; 1300 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt;= 1483</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="-76.85872922808787" y="103.30862753577674" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-125.39064252488151" y="104.66007612753242" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 1300</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="-94.04298189366253" y="78.49505709565221" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 1116</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="-59.67447656251284" y="128.12219797590149" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt; 1116 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt;= 1300</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="51.552757996724694" y="74.44071132037868" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 1116</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="16">
            <position x="-28.326815931292657" y="101.95717894402048" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="17">
            <position x="-62.69532126244246" y="52.33003806376678" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 933</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="18">
            <position x="-156.73830315610053" y="130.82509515941535" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt; 1483</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&gt; 1483</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="19">
            <position x="-11.142563265717747" y="126.77074938414648" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &gt; 933 AND STEEL_TEMPERATURE_GRAB1_CELSIUS_DEG &lt;= 1116</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="20">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="21">
            <position x="34.36850533114986" y="49.62714088025257" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 1300</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="5" to="0" />
        <edge from="21" to="0" />
        <edge from="20" to="1" />
        <edge from="20" to="2" />
        <edge from="15" to="3" />
        <edge from="0" to="4" />
        <edge from="15" to="4" />
        <edge from="1" to="5" />
        <edge from="2" to="5" />
        <edge from="3" to="6" />
        <edge from="6" to="7" />
        <edge from="8" to="7" />
        <edge from="10" to="7" />
        <edge from="14" to="7" />
        <edge from="18" to="7" />
        <edge from="19" to="7" />
        <edge from="3" to="8" />
        <edge from="4" to="8" />
        <edge from="5" to="9" />
        <edge from="17" to="9" />
        <edge from="11" to="10" />
        <edge from="12" to="10" />
        <edge from="13" to="11" />
        <edge from="9" to="11" />
        <edge from="13" to="12" />
        <edge from="17" to="13" />
        <edge from="11" to="14" />
        <edge from="16" to="14" />
        <edge from="21" to="15" />
        <edge from="0" to="16" />
        <edge from="9" to="16" />
        <edge from="2" to="17" />
        <edge from="12" to="18" />
        <edge from="4" to="19" />
        <edge from="16" to="19" />
        <edge from="1" to="21" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
    <diagram title="Equipment Health All Combinations">
        <node id="0">
            <position x="-245.4126677853152" y="274.4249963404201" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Healthy</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="54.04409256921207" y="336.2997343856674" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-324.5229621256783" y="487.45662107430394" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="413.58722558587795" y="156.04212420305203" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="89.06426346019998" y="643.4987452773523" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="334.4769312455146" y="369.0737489369362" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="220.34646601416478" y="274.9063627791296" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="35.02017089098689" y="307.19901089168945" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="114.13046523135031" y="94.1673861578061" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Critical</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="-79.11029434036334" y="213.03162473388295" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Low</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="299.45676035452806" y="61.87473804524632" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Medium</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="-25.066201771150133" y="549.331359119549" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-131.28220255396457" y="368.5923824982268" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="-210.39249689432825" y="581.6240072321095" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="168.17455780056378" y="430.46712054347404" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Healthy') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Medium') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Low') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE rul_fca_bin='Critical')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="13" to="0" />
        <edge from="0" to="1" />
        <edge from="10" to="1" />
        <edge from="0" to="2" />
        <edge from="9" to="2" />
        <edge from="10" to="3" />
        <edge from="8" to="3" />
        <edge from="5" to="4" />
        <edge from="11" to="4" />
        <edge from="14" to="4" />
        <edge from="15" to="4" />
        <edge from="3" to="5" />
        <edge from="6" to="5" />
        <edge from="7" to="5" />
        <edge from="10" to="6" />
        <edge from="9" to="6" />
        <edge from="8" to="7" />
        <edge from="9" to="7" />
        <edge from="13" to="8" />
        <edge from="13" to="9" />
        <edge from="13" to="10" />
        <edge from="1" to="11" />
        <edge from="2" to="11" />
        <edge from="6" to="11" />
        <edge from="0" to="12" />
        <edge from="8" to="12" />
        <edge from="2" to="14" />
        <edge from="12" to="14" />
        <edge from="7" to="14" />
        <edge from="1" to="15" />
        <edge from="12" to="15" />
        <edge from="3" to="15" />
        <projectionBase>
            <vector x="80.5" y="82.5" />
            <vector x="33.0" y="50.0" />
            <vector x="-17.0" y="60.0" />
            <vector x="-147.0" y="170.0" />
        </projectionBase>
    </diagram>
    <diagram title="Steel Types">
        <node id="0">
            <position x="-537.9032573699965" y="137.00228023529" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="152.07934570312426" y="446.6822369893399" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="32.78673489888503" y="288.95428975423226" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>St3sp</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-83.92280515035075" y="151.27245362599714" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="286.6365315119423" y="85.99906031290679" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>Arm500</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-337.77260176340826" y="354.2276830673231" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="-505.11652247111215" y="425.9565699895234" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="-366.8266369501752" y="50.034974733988406" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>1015</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="119.29261080423993" y="157.7279472351071" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="-167.3439207077028" y="71.72888692220059" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>YP</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="-51.136070251466464" y="440.2267433802273" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-134.5571858088175" y="360.683176676433" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="319.4232664108275" y="374.95335006714026" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="-251.26672585805426" y="223.00134054819762" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND  NOT (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="-218.47999095916936" y="511.95563030242624" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>(SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='Arm500') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='YP') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='St3sp') AND (SELECT datetime_combined FROM PreProcessedDataset WHERE steel_type='1015')</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <edge from="8" to="0" />
        <edge from="10" to="0" />
        <edge from="9" to="1" />
        <edge from="12" to="1" />
        <edge from="13" to="1" />
        <edge from="6" to="2" />
        <edge from="8" to="3" />
        <edge from="4" to="3" />
        <edge from="6" to="4" />
        <edge from="2" to="5" />
        <edge from="8" to="5" />
        <edge from="0" to="7" />
        <edge from="5" to="7" />
        <edge from="12" to="7" />
        <edge from="6" to="8" />
        <edge from="10" to="9" />
        <edge from="4" to="9" />
        <edge from="6" to="10" />
        <edge from="5" to="11" />
        <edge from="13" to="11" />
        <edge from="3" to="11" />
        <edge from="2" to="12" />
        <edge from="10" to="12" />
        <edge from="2" to="13" />
        <edge from="4" to="13" />
        <edge from="0" to="14" />
        <edge from="9" to="14" />
        <edge from="3" to="14" />
        <edge from="1" to="15" />
        <edge from="7" to="15" />
        <edge from="11" to="15" />
        <edge from="14" to="15" />
        <projectionBase>
            <vector x="80.5" y="82.5" />
            <vector x="33.0" y="50.0" />
            <vector x="-17.0" y="60.0" />
            <vector x="-147.0" y="170.0" />
        </projectionBase>
    </diagram>
    <diagram title="INTERORDINAL_WATER_CONSUMPTION_DECREASING">
        <node id="0">
            <position x="-49.20156230580872" y="134.66571109492793" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt; 1555 AND WATER_CONSUMPTION_LITER_MINUTE &lt;= 1705</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="1">
            <position x="39.45631816013351" y="135.24155296644653" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt; 1855 AND WATER_CONSUMPTION_LITER_MINUTE &lt;= 2005</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="2">
            <position x="-82.71566566305185" y="80.45392153404214" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 1705</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="3">
            <position x="-25.655778884887695" y="171.63760375976562" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="4">
            <position x="-38.38672543007962" y="80.74184246980315" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="5">
            <position x="-55.14377710870065" y="53.63594768936207" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 1855</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="6">
            <position x="67.02820671448472" y="108.42357912176567" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 1855</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>4.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="7">
            <position x="-137.85944277175372" y="134.08986922340887" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &lt;= 1405</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&lt;= 1405</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>5.0</coordinate>
            </ndimVector>
        </node>
        <node id="8">
            <position x="-27.571888554350323" y="26.817973844680978" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 2005</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="9">
            <position x="-93.53050253878223" y="134.37779015916817" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt; 1405 AND WATER_CONSUMPTION_LITER_MINUTE &lt;= 1555</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="10">
            <position x="0.0" y="0.0" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="11">
            <position x="-21.62967375145857" y="107.84773725024411" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="12">
            <position x="-10.81483687572949" y="53.92386862512234" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="13">
            <position x="50.27115503586292" y="81.31768434132414" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 1705</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="14">
            <position x="-110.287554217403" y="107.2718953787271" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&lt;= 1555</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>0.0</coordinate>
                <coordinate>4.0</coordinate>
            </ndimVector>
        </node>
        <node id="15">
            <position x="-4.872622072837672" y="134.95363203068655" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt; 1705 AND WATER_CONSUMPTION_LITER_MINUTE &lt;= 1855</object>
                </objectContingent>
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>2.0</coordinate>
            </ndimVector>
        </node>
        <node id="16">
            <position x="22.699266481512396" y="108.13565818600466" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>3.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="17">
            <position x="33.51410335724208" y="54.21178956088289" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 1555</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="18">
            <position x="-65.95861398443017" y="107.55981631448651" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>3.0</coordinate>
            </ndimVector>
        </node>
        <node id="19">
            <position x="5.942214802891522" y="81.02976340556359" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent />
            </concept>
            <ndimVector>
                <coordinate>2.0</coordinate>
                <coordinate>1.0</coordinate>
            </ndimVector>
        </node>
        <node id="20">
            <position x="16.757051678620982" y="27.105894780441474" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent />
                <attributeContingent>
                    <attribute>&gt; 1405</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>1.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <node id="21">
            <position x="83.78525839310572" y="135.52947390220697" />
            <attributeLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </attributeLabelStyle>
            <objectLabelStyle>
                <offset x="0.0" y="0.0" />
                <backgroundColor>#ffffffff</backgroundColor>
                <textColor>#ff000000</textColor>
                <textAlignment>left</textAlignment>
            </objectLabelStyle>
            <concept>
                <objectContingent>
                    <object>WATER_CONSUMPTION_LITER_MINUTE &gt; 2005</object>
                </objectContingent>
                <attributeContingent>
                    <attribute>&gt; 2005</attribute>
                </attributeContingent>
            </concept>
            <ndimVector>
                <coordinate>5.0</coordinate>
                <coordinate>0.0</coordinate>
            </ndimVector>
        </node>
        <edge from="11" to="0" />
        <edge from="18" to="0" />
        <edge from="16" to="1" />
        <edge from="6" to="1" />
        <edge from="5" to="2" />
        <edge from="0" to="3" />
        <edge from="1" to="3" />
        <edge from="7" to="3" />
        <edge from="9" to="3" />
        <edge from="15" to="3" />
        <edge from="21" to="3" />
        <edge from="12" to="4" />
        <edge from="5" to="4" />
        <edge from="8" to="5" />
        <edge from="13" to="6" />
        <edge from="14" to="7" />
        <edge from="10" to="8" />
        <edge from="14" to="9" />
        <edge from="18" to="9" />
        <edge from="4" to="11" />
        <edge from="19" to="11" />
        <edge from="8" to="12" />
        <edge from="20" to="12" />
        <edge from="17" to="13" />
        <edge from="2" to="14" />
        <edge from="11" to="15" />
        <edge from="16" to="15" />
        <edge from="13" to="16" />
        <edge from="19" to="16" />
        <edge from="20" to="17" />
        <edge from="2" to="18" />
        <edge from="4" to="18" />
        <edge from="12" to="19" />
        <edge from="17" to="19" />
        <edge from="10" to="20" />
        <edge from="6" to="21" />
        <projectionBase>
            <vector x="52.0" y="120.0" />
            <vector x="-108.0" y="200.0" />
        </projectionBase>
    </diagram>
</conceptualSchema>

