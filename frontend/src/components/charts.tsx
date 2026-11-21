import { ReactNode } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LEVEL_COLOR } from "../utils/format";
import { Card, EmptyState } from "./ui";

const AX = { fontSize: 11, fill: "#5B6B8C" };
const GRID = "#EDF0F6";
const PALETTE = ["#F36F21", "#1B2A4A", "#8592AD", "#FF8C42", "#2E3F63", "#B5BFD3", "#D95A12", "#5B6B8C"];
const tip = { contentStyle: { borderRadius: 8, border: "1px solid #DCE2EE", fontSize: 12, boxShadow: "0 8px 24px rgba(16,27,51,.14)" } };

export const ChartCard = ({ title, children, empty, className = "" }: { title: string; children: ReactNode; empty?: boolean; className?: string }) => (
  <Card title={title} className={className}>{empty ? <EmptyState title="No data yet" hint="Seed the database or run an investigation." /> : <div className="h-64">{children}</div>}</Card>
);

export function BarSimple({ data, x = "label", y = "count", horizontal = false, color = "#F36F21", colorBy }: { data: object[]; x?: string; y?: string; horizontal?: boolean; color?: string; colorBy?: (d: never) => string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: horizontal ? 24 : 0, right: 8, top: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={!horizontal} horizontal={horizontal ? false : true} />
        {horizontal ? <><XAxis type="number" tick={AX} allowDecimals={false} /><YAxis type="category" dataKey={x} tick={AX} width={92} /></> : <><XAxis dataKey={x} tick={AX} interval={0} angle={data.length > 8 ? -30 : 0} height={data.length > 8 ? 52 : 28} textAnchor={data.length > 8 ? "end" : "middle"} /><YAxis tick={AX} allowDecimals={false} /></>}
        <Tooltip {...tip} cursor={{ fill: "#F6F8FB" }} />
        <Bar dataKey={y} fill={color} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}>{colorBy && data.map((d, i) => <Cell key={i} fill={colorBy(d as never)} />)}</Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AreaSimple({ data, x = "date", y = "count" }: { data: object[]; x?: string; y?: string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ right: 8, top: 4 }}>
        <defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#F36F21" stopOpacity={0.35} /><stop offset="100%" stopColor="#F36F21" stopOpacity={0} /></linearGradient></defs>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} /><XAxis dataKey={x} tick={AX} /><YAxis tick={AX} allowDecimals={false} /><Tooltip {...tip} />
        <Area type="monotone" dataKey={y} stroke="#F36F21" strokeWidth={2} fill="url(#ar)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function LinesTwo({ data, x, a, b, aName, bName }: { data: object[]; x: string; a: string; b: string; aName: string; bName: string }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ right: 8, top: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} /><XAxis dataKey={x} tick={AX} /><YAxis tick={AX} allowDecimals={false} /><Tooltip {...tip} /><Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey={a} name={aName} stroke="#1B2A4A" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey={b} name={bName} stroke="#F36F21" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function Donut({ data, levelColors = false }: { data: { label: string; count: number }[]; levelColors?: boolean }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie data={data} dataKey="count" nameKey="label" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
          {data.map((d, i) => <Cell key={d.label} fill={levelColors ? LEVEL_COLOR[d.label] ?? PALETTE[i] : PALETTE[i % PALETTE.length]} />)}
        </Pie>
        <Tooltip {...tip} /><Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
