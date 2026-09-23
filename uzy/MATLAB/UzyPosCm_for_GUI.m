function [vr,newTtr]=UzyPosCm_for_GUI(f,v)
%
[r,~]=find(isnan(f));
if ~isempty(r)
    r=unique(r);
    %disp(['Found in f ',num2str(r),' rows with NaNs; erased']);
    f(r,:)=[];
end
fn=facenormals(f,v);% fn is assumed to be free of NaN's !
tra=sqrt(dot(fn,fn,2)); %a vector of norms; the area of a tiangle is half the norm
for i=1:3
    u(:,i)=fn(:,i)./tra;
end %unit normals
[r,~]=find(isinf(u) | isnan(u));
if ~isempty(r)
    r=unique(r);
    %warning(['found ',num2str(length(r)),' irregulars... putting zeros instead']);
    u(r,:)=0;
end
%
tra=tra/2; %area of individual triangles
SA=sum(tra);%total surface area
[Ttr]=Norm2Posing_for_GUI(u,tra,SA); %the transform
[vr,newTtr]=Ult2Pose_for_GUI(v,f,Ttr);%rotate (perhaps invert) and display



function [vct,InvTrr]=Ult2Pose_for_GUI(vcm,f,Tr)
%
vct=inv(Tr)*vcm';
vct=vct'; %rotated per Tr
midz=(max(vct(:,3))+min(vct(:,3)))/2;
if midz<0 %if the center of mass is above half-height, rotate the new frame 180 about x
    InvTrr=[1 0 0;0 -1 0;0 0 -1]*inv(Tr);
    vct=InvTrr*vcm';
    vct=vct';
    %disp('rotated 180 deg about x');
else
    InvTrr=inv(Tr);
end

%
